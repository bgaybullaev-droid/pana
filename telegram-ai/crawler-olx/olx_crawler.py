"""
OLX.uz Crawler - Playwright-based Web Crawler

Crawls real estate listings from OLX.uz:
1. Go to category page (e.g., https://www.olx.uz/nedvizhimost/)
2. Collect all listing URLs from the page
3. Enter each listing URL, convert HTML → Markdown → JSON
4. Go to next page, repeat

Usage:
    python olx_crawler.py
    python olx_crawler.py --category apartments
    python olx_crawler.py --max-pages 5
    python olx_crawler.py --headless=false
    python olx_crawler.py --url https://www.olx.uz/d/obyavlenie/3-honali-kvartira-ID4hiGs.html
"""

import asyncio
import json
import os
import re
import sys
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime
from urllib.parse import urljoin, urlparse
import aiohttp
import yaml

# Playwright for browser automation
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# Local imports
from config import (
    OLX_BASE_URL,
    CATEGORIES,
    MAX_PAGES_PER_CATEGORY,
    DELAY_BETWEEN_REQUESTS,
    DELAY_BETWEEN_LISTINGS,
    REQUEST_TIMEOUT,
    HEADLESS,
    USER_AGENT,
    OUTPUT_DIR,
    MARKDOWN_DIR,
    JSON_DIR,
    IMAGES_DIR,
    CATEGORY_SELECTORS,
    LISTING_SELECTORS,
    FILTERS,
    VERBOSE,
    REAL_ESTATE_KEYWORDS,
    SELLER_PROFILE_SELECTORS,
    MAX_SELLER_PROFILE_PAGES,
)

from bs4 import BeautifulSoup
from html_to_markdown import html_to_listing_markdown
from olx_extractor import OLXExtractor

# Import OLX-specific backend_push (not the Telegram one on sys.path)
import importlib.util
_bp_spec = importlib.util.spec_from_file_location(
    "olx_backend_push", Path(__file__).parent / "backend_push.py"
)
_bp_mod = importlib.util.module_from_spec(_bp_spec)
_bp_spec.loader.exec_module(_bp_mod)
push_to_backend = _bp_mod.push_listing
push_listing_with_local_images = _bp_mod.push_listing_with_local_images

# Add parent crawler directory to path for vector_db
CRAWLER_DIR = Path(__file__).parent.parent / "crawler"
sys.path.insert(0, str(CRAWLER_DIR))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if VERBOSE else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent / 'crawler.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class OLXCrawler:
    """
    Playwright-based crawler for OLX.uz real estate listings

    Workflow:
    1. Go to category page
    2. Collect all listing URLs
    3. Enter each listing URL, convert HTML → Markdown → JSON
    4. Go to next page, repeat
    """

    def __init__(self, headless: bool = HEADLESS, force_update: bool = False, provider: str = None):
        """
        Initialize the OLX crawler

        Args:
            headless: Run browser in headless mode
            force_update: If True, re-crawl previously processed listings for update detection
            provider: LLM provider override ('anthropic', 'openai', 'gemini')
        """
        self.headless = headless
        self.force_update = force_update
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Initialize extractor
        self.extractor = OLXExtractor(provider=provider)

        # Track processed listings to avoid duplicates
        self.processed_ids: Set[str] = set()

        # Track visited seller profiles
        self.visited_sellers: Set[str] = set()

        # Statistics
        self.stats = {
            'pages_crawled': 0,
            'listings_found': 0,
            'listings_processed': 0,
            'listings_failed': 0,
            'duplicates_skipped': 0,
            'seller_profiles_visited': 0,
            'seller_listings_found': 0,
            'start_time': None,
            'end_time': None,
        }

        # Load processed IDs from existing JSON files (skip in force-update mode)
        if not self.force_update:
            self._load_processed_ids()
        else:
            logger.info("Force-update mode: skipping processed IDs cache")

    def _load_processed_ids(self):
        """Load previously processed listing IDs"""
        for json_file in JSON_DIR.glob('*.json'):
            listing_id = json_file.stem
            self.processed_ids.add(listing_id)

        if self.processed_ids:
            logger.info(f"Loaded {len(self.processed_ids)} previously processed listings")

    def _extract_listing_id(self, url: str) -> Optional[str]:
        """
        Extract listing ID from OLX URL

        Example: https://www.olx.uz/d/obyavlenie/3-honali-kvartira-ID4hiGs.html
        Returns: ID4hiGs
        """
        match = re.search(r'-(ID[a-zA-Z0-9]+)\.html', url)
        if match:
            return match.group(1)

        # Alternative pattern
        match = re.search(r'/([a-zA-Z0-9]+)\.html$', url)
        if match:
            return match.group(1)

        return None

    def get_seller_profile_url(self, html: str) -> Optional[str]:
        """Extract seller profile URL from listing page HTML."""
        soup = BeautifulSoup(html, 'lxml')
        seller_el = soup.select_one('[data-testid="seller_card"], [data-testid="seller-card"]')
        if not seller_el:
            return None

        seller_link = seller_el.select_one('a[href*="/list/user/"], a[href*="/d/user/"], a[href*="/profile/"]')
        if not seller_link:
            return None

        href = seller_link.get('href', '')
        if href:
            return urljoin(OLX_BASE_URL, href)
        return None

    async def is_real_estate_card(self, card) -> bool:
        """Check if a listing card belongs to a real estate category."""
        try:
            text = (await card.inner_text()).lower()
            return any(kw in text for kw in REAL_ESTATE_KEYWORDS)
        except Exception:
            return False

    async def get_seller_listing_urls(self, profile_url: str) -> List[str]:
        """Collect real estate listing URLs from a seller's profile page."""
        urls = []
        seen = set()

        for page_num in range(1, MAX_SELLER_PROFILE_PAGES + 1):
            if page_num == 1:
                current_url = profile_url
            else:
                separator = '&' if '?' in profile_url else '?'
                current_url = f"{profile_url}{separator}page={page_num}"

            try:
                await self.page.goto(current_url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(DELAY_BETWEEN_REQUESTS)

                cards = await self.page.query_selector_all(
                    SELLER_PROFILE_SELECTORS['listing_cards']
                )

                if not cards:
                    break

                page_found = 0
                for card in cards:
                    # Filter for real estate only
                    if not await self.is_real_estate_card(card):
                        continue

                    link = await card.query_selector(
                        SELLER_PROFILE_SELECTORS['listing_link']
                    )
                    if not link:
                        continue

                    href = await link.get_attribute('href')
                    if not href:
                        continue

                    full_url = urljoin(OLX_BASE_URL, href)
                    if '/d/obyavlenie/' in full_url and full_url not in seen:
                        listing_id = self._extract_listing_id(full_url)
                        if listing_id and listing_id not in self.processed_ids:
                            seen.add(full_url)
                            urls.append(full_url)
                            page_found += 1

                logger.info(
                    f"Seller profile page {page_num}: "
                    f"found {page_found} new real estate listings"
                )

                # Check for next page
                next_btn = await self.page.query_selector(
                    SELLER_PROFILE_SELECTORS['next_page']
                )
                if not next_btn:
                    break

            except Exception as e:
                logger.error(f"Error crawling seller profile page {page_num}: {e}")
                break

        return urls

    async def crawl_seller_profile(self, profile_url: str):
        """Visit a seller's profile and crawl their real estate listings."""
        if profile_url in self.visited_sellers:
            return

        self.visited_sellers.add(profile_url)
        self.stats['seller_profiles_visited'] += 1
        logger.info(f"Visiting seller profile: {profile_url}")

        listing_urls = await self.get_seller_listing_urls(profile_url)
        self.stats['seller_listings_found'] += len(listing_urls)

        if not listing_urls:
            logger.info("No new real estate listings found on seller profile")
            return

        logger.info(
            f"Found {len(listing_urls)} real estate listings from seller profile"
        )

        for url in listing_urls:
            await self.crawl_listing(url)

    async def init_browser(self):
        """Initialize Playwright browser"""
        logger.info("Initializing Playwright browser...")

        playwright = await async_playwright().start()

        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )

        self.context = await self.browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1920, 'height': 1080},
            locale='ru-RU',
        )

        self.page = await self.context.new_page()

        # Set default timeout
        self.page.set_default_timeout(REQUEST_TIMEOUT)

        logger.info("✅ Browser initialized")

    async def close_browser(self):
        """Close browser and cleanup"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

        logger.info("Browser closed")

    async def get_listing_urls(self, category_url: str) -> List[str]:
        """
        STEP 1: Go to category page, collect all listing URLs

        Args:
            category_url: Category page URL (e.g., https://www.olx.uz/nedvizhimost/)

        Returns:
            List of listing URLs found on the page
        """
        logger.info(f"Collecting listing URLs from: {category_url}")

        try:
            await self.page.goto(category_url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(DELAY_BETWEEN_REQUESTS)

            # Wait for listing cards to load
            await self.page.wait_for_selector(
                CATEGORY_SELECTORS['listing_cards'],
                timeout=10000
            )

            # Find all listing links
            links = await self.page.query_selector_all(CATEGORY_SELECTORS['listing_link'])

            urls = []
            seen_urls = set()

            for link in links:
                href = await link.get_attribute('href')
                if href:
                    # Make absolute URL
                    full_url = urljoin(OLX_BASE_URL, href)

                    # Check if it's a listing URL (not promoted/ad)
                    if '/d/obyavlenie/' in full_url and full_url not in seen_urls:
                        seen_urls.add(full_url)
                        urls.append(full_url)

            logger.info(f"Found {len(urls)} listing URLs on page")
            return urls

        except Exception as e:
            logger.error(f"Error collecting listing URLs: {e}")
            return []

    async def crawl_listing(self, listing_url: str) -> Optional[tuple]:
        """
        STEP 2: Enter one listing URL and convert HTML → Markdown → JSON

        Args:
            listing_url: Individual listing URL

        Returns:
            (extracted_data, seller_profile_url) or None if failed
        """
        listing_id = self._extract_listing_id(listing_url)

        if not listing_id:
            logger.warning(f"Could not extract ID from URL: {listing_url}")
            return None

        # Skip if already processed
        if listing_id in self.processed_ids:
            logger.debug(f"Skipping already processed: {listing_id}")
            self.stats['duplicates_skipped'] += 1
            return None

        logger.info(f"Crawling listing: {listing_id}")

        try:
            # Go to listing page
            await self.page.goto(listing_url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(DELAY_BETWEEN_LISTINGS)

            # Get HTML content
            html = await self.page.content()

            # Extract seller profile URL before converting to markdown
            seller_profile_url = self.get_seller_profile_url(html)

            # Convert HTML → Markdown
            markdown, raw_data = html_to_listing_markdown(html)

            if not markdown or len(markdown) < 50:
                logger.warning(f"Insufficient content for {listing_id}")
                self.stats['listings_failed'] += 1
                return None

            # Save markdown for debugging
            markdown_file = MARKDOWN_DIR / f"{listing_id}.md"
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(f"# Listing: {listing_id}\n")
                f.write(f"URL: {listing_url}\n")
                f.write(f"Crawled: {datetime.now().isoformat()}\n")
                f.write("---\n\n")
                f.write(markdown)

            # Extract JSON from Markdown
            extracted_data = self.extractor.extract(
                markdown=markdown,
                listing_id=listing_id,
                images=raw_data.get('images', [])
            )

            if not extracted_data:
                logger.warning(f"Extraction failed for {listing_id}")
                self.stats['listings_failed'] += 1
                return None

            # Add metadata
            extracted_data['olx_id'] = listing_id
            extracted_data['url'] = listing_url
            extracted_data['crawled_at'] = datetime.now().isoformat()
            extracted_data['raw_text'] = markdown

            # Save JSON
            json_file = JSON_DIR / f"{listing_id}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, ensure_ascii=False, indent=2)

            # Download images and push to backend
            image_urls = raw_data.get('images', [])[:12]
            if image_urls:
                # Download images locally first
                await self._download_images(listing_id, image_urls)

                # Collect downloaded file paths
                listing_images_dir = IMAGES_DIR / listing_id
                local_paths = sorted(str(p) for p in listing_images_dir.glob("*") if p.is_file())

                if local_paths:
                    # Upload local images to backend and push listing
                    push_listing_with_local_images(extracted_data, local_paths)
                elif image_urls:
                    # Fallback: use OLX CDN URLs directly
                    extracted_data['images'] = image_urls
                    push_to_backend(extracted_data)
            elif image_urls:
                # No download configured, use CDN URLs directly
                extracted_data['images'] = image_urls
                push_to_backend(extracted_data)

            # Mark as processed
            self.processed_ids.add(listing_id)
            self.stats['listings_processed'] += 1

            logger.info(f"Processed: {listing_id} - {extracted_data.get('property_type', 'unknown')}")
            return extracted_data, seller_profile_url

        except Exception as e:
            logger.error(f"Error crawling {listing_url}: {e}")
            self.stats['listings_failed'] += 1
            return None

    async def _download_images(self, listing_id: str, image_urls: List[str]):
        """Download listing images"""
        listing_images_dir = IMAGES_DIR / listing_id
        listing_images_dir.mkdir(exist_ok=True)

        async with aiohttp.ClientSession() as session:
            for i, url in enumerate(image_urls, 1):
                try:
                    async with session.get(url, timeout=30) as response:
                        if response.status == 200:
                            content = await response.read()
                            ext = 'jpg'
                            if 'png' in url.lower():
                                ext = 'png'
                            image_file = listing_images_dir / f"{i}.{ext}"
                            with open(image_file, 'wb') as f:
                                f.write(content)
                            logger.debug(f"Downloaded image {i} for {listing_id}")
                except Exception as e:
                    logger.warning(f"Failed to download image {i} for {listing_id}: {e}")

    async def has_next_page(self) -> bool:
        """Check if there's a next page button"""
        try:
            next_btn = await self.page.query_selector(CATEGORY_SELECTORS['next_page'])
            return next_btn is not None
        except:
            return False

    async def go_to_next_page(self) -> bool:
        """Click next page button"""
        try:
            next_btn = await self.page.query_selector(CATEGORY_SELECTORS['next_page'])
            if next_btn:
                await next_btn.click()
                await self.page.wait_for_load_state('domcontentloaded')
                await asyncio.sleep(DELAY_BETWEEN_REQUESTS)
                return True
        except Exception as e:
            logger.error(f"Error navigating to next page: {e}")
        return False

    async def crawl_category(self, category_path: str, max_pages: int = MAX_PAGES_PER_CATEGORY):
        """
        Crawl all listings in a category with pagination

        Args:
            category_path: Category path (e.g., /nedvizhimost/)
            max_pages: Maximum number of pages to crawl
        """
        category_url = urljoin(OLX_BASE_URL, category_path)
        logger.info(f"Starting category crawl: {category_url}")

        page_num = 1

        while page_num <= max_pages:
            logger.info(f"=== Page {page_num}/{max_pages} ===")

            # Get listing URLs from current page
            if page_num == 1:
                current_url = category_url
            else:
                current_url = f"{category_url}?page={page_num}"

            listing_urls = await self.get_listing_urls(current_url)
            self.stats['listings_found'] += len(listing_urls)
            self.stats['pages_crawled'] += 1

            if not listing_urls:
                logger.info("No more listings found, stopping")
                break

            # Crawl each listing
            for url in listing_urls:
                result = await self.crawl_listing(url)
                if result:
                    _, seller_profile_url = result
                    # Crawl seller's other real estate listings
                    if seller_profile_url and seller_profile_url not in self.visited_sellers:
                        await self.crawl_seller_profile(seller_profile_url)

            # Check for next page
            page_num += 1
            if page_num > max_pages:
                logger.info(f"Reached max pages limit ({max_pages})")
                break

            # Check if next page exists
            if not await self.has_next_page():
                logger.info("No next page button found, stopping")
                break

        logger.info(f"Category crawl complete: {category_path}")

    async def run_single(self, url: str):
        """
        Crawl a single OLX listing by URL and push to backend

        Args:
            url: Full OLX listing URL (e.g., https://www.olx.uz/d/obyavlenie/...)
        """
        self.stats['start_time'] = datetime.now()

        logger.info("=" * 60)
        logger.info("OLX.uz Single Listing Crawl")
        logger.info(f"URL: {url}")
        logger.info("=" * 60)

        try:
            await self.init_browser()

            # Force-crawl even if previously processed
            listing_id = self._extract_listing_id(url)
            if listing_id:
                self.processed_ids.discard(listing_id)

            result = await self.crawl_listing(url)

            if result:
                extracted_data, _ = result
                logger.info(f"✅ Successfully crawled and imported: {url}")
                logger.info(f"   Property: {extracted_data.get('property_type', '?')}, "
                           f"Price: {extracted_data.get('price', '?')} {extracted_data.get('currency', '')}, "
                           f"Rooms: {extracted_data.get('rooms', '?')}")
            else:
                logger.error(f"❌ Failed to crawl: {url}")

        except Exception as e:
            logger.error(f"Crawler error: {e}")
            raise

        finally:
            await self.close_browser()
            self.stats['end_time'] = datetime.now()
            self._print_stats()

    async def run(self, category: str = "all_real_estate", max_pages: int = MAX_PAGES_PER_CATEGORY):
        """
        Main entry point - run the crawler

        Args:
            category: Category key from CATEGORIES dict
            max_pages: Maximum pages to crawl
        """
        self.stats['start_time'] = datetime.now()

        logger.info("=" * 60)
        logger.info("OLX.uz Crawler Starting")
        logger.info(f"Category: {category}")
        logger.info(f"Max pages: {max_pages}")
        logger.info("=" * 60)

        try:
            # Initialize browser
            await self.init_browser()

            # Get category path
            category_path = CATEGORIES.get(category)
            if not category_path:
                logger.error(f"Unknown category: {category}")
                logger.info(f"Available categories: {list(CATEGORIES.keys())}")
                return

            # Crawl the category
            await self.crawl_category(category_path, max_pages)

        except Exception as e:
            logger.error(f"Crawler error: {e}")
            raise

        finally:
            # Cleanup
            await self.close_browser()
            self.stats['end_time'] = datetime.now()
            self._print_stats()

    def _print_stats(self):
        """Print crawl statistics"""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()

        logger.info("\n" + "=" * 60)
        logger.info("CRAWL STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Pages crawled:          {self.stats['pages_crawled']}")
        logger.info(f"Listings found:         {self.stats['listings_found']}")
        logger.info(f"Listings processed:     {self.stats['listings_processed']}")
        logger.info(f"Listings failed:        {self.stats['listings_failed']}")
        logger.info(f"Duplicates skipped:     {self.stats['duplicates_skipped']}")
        logger.info(f"Seller profiles visited:{self.stats['seller_profiles_visited']}")
        logger.info(f"Seller listings found:  {self.stats['seller_listings_found']}")
        logger.info(f"Duration:               {duration:.1f} seconds")

        if self.stats['listings_processed'] > 0:
            avg_time = duration / self.stats['listings_processed']
            logger.info(f"Avg time/listing:       {avg_time:.2f} seconds")

        logger.info("=" * 60)


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description='OLX.uz Real Estate Crawler')

    parser.add_argument(
        '--url',
        type=str,
        default=None,
        help='Crawl a single OLX listing by URL'
    )

    parser.add_argument(
        '--category',
        type=str,
        default='all_real_estate',
        choices=list(CATEGORIES.keys()),
        help='Category to crawl'
    )

    parser.add_argument(
        '--max-pages',
        type=int,
        default=MAX_PAGES_PER_CATEGORY,
        help='Maximum number of pages to crawl'
    )

    parser.add_argument(
        '--headless',
        type=str,
        default='true',
        choices=['true', 'false'],
        help='Run browser in headless mode'
    )

    parser.add_argument(
        '--force-update',
        action='store_true',
        default=False,
        help='Re-crawl previously processed listings for update detection'
    )

    parser.add_argument(
        '--provider',
        type=str,
        default=None,
        choices=['anthropic', 'openai', 'gemini', 'ollama'],
        help='LLM provider to use (default: LLM_PROVIDER from .env)'
    )

    parser.add_argument(
        '--list-categories',
        action='store_true',
        help='List available categories'
    )

    args = parser.parse_args()

    if args.list_categories:
        print("\nAvailable categories:")
        for key, path in CATEGORIES.items():
            print(f"  {key}: {OLX_BASE_URL}{path}")
        return

    headless = args.headless.lower() == 'true'

    # Single URL mode
    if args.url:
        crawler = OLXCrawler(headless=headless, force_update=True, provider=args.provider)
        asyncio.run(crawler.run_single(args.url))
        return

    # Category crawl mode
    crawler = OLXCrawler(headless=headless, force_update=args.force_update, provider=args.provider)

    # Run the async crawler
    asyncio.run(crawler.run(
        category=args.category,
        max_pages=args.max_pages
    ))


if __name__ == '__main__':
    main()
