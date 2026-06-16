"""
OLX.uz Crawler for n8n - Supports OpenAI and Gemini LLMs, outputs JSON array

Crawls real estate listings from OLX.uz and outputs a single JSON file
compatible with n8n workflow automation.

Usage:
    python olx_crawler_n8n.py
    python olx_crawler_n8n.py --provider gemini
    python olx_crawler_n8n.py --provider openai
    python olx_crawler_n8n.py --category apartments
    python olx_crawler_n8n.py --max-pages 5
    python olx_crawler_n8n.py --output listings.json
"""

import asyncio
import json
import re
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime
from urllib.parse import urljoin
import os

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
    CATEGORY_SELECTORS,
    LISTING_SELECTORS,
    REAL_ESTATE_KEYWORDS,
    SELLER_PROFILE_SELECTORS,
    MAX_SELLER_PROFILE_PAGES,
)

from bs4 import BeautifulSoup
from html_to_markdown import html_to_listing_markdown

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent / 'crawler_n8n.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class ListingExtractor:
    """Extract structured data using OpenAI, Gemini, or Ollama"""

    EXTRACTION_PROMPT = """You are a real estate data extraction specialist for Uzbekistan.
Extract structured data from this OLX.uz listing and return ONLY valid JSON.

FIELDS TO EXTRACT:
- property_type: "apartment", "house", "commercial", "land", or "office"
- listing_type: "sale", "rent", or "daily_rent"
- price: number (without currency symbol)
- currency: "USD" or "UZS"
- rooms: number of rooms (integer)
- area_sqm: area in square meters (number)
- floor: floor number (integer)
- total_floors: total floors in building (integer)
- district: district/region name
- address: specific address or landmarks
- description: brief description in the ORIGINAL language of the listing (max 100 chars) — do NOT translate
- amenities: array of amenities like ["furniture", "parking", "gas"]
- contact_phone: phone in +998XXXXXXXXX format

PRICE PARSING:
- "85.000 у.е." or "85,000$" -> price: 85000, currency: "USD"
- "350 mln so'm" -> price: 350000000, currency: "UZS"
- у.е., $, dollar, y.e. = USD
- сум, so'm, sum = UZS

LISTING:
```
{markdown}
```

Return ONLY valid JSON object. No explanation, no markdown code blocks."""

    def __init__(self, provider: str = None):
        """Initialize LLM client based on provider selection"""
        self.provider = provider or os.getenv('LLM_PROVIDER', 'gemini')

        if self.provider == 'gemini':
            import google.generativeai as genai
            api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not set in .env")
            genai.configure(api_key=api_key)
            model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite')
            self.gemini_model = genai.GenerativeModel(model_name)
            self._genai = genai
            logger.info(f"Initialized Gemini with model: {model_name}")

        elif self.provider == 'openai':
            import openai
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in .env")
            self.openai_client = openai.OpenAI(api_key=api_key)
            self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
            logger.info(f"Initialized OpenAI with model: {self.openai_model}")

        elif self.provider == 'ollama':
            import openai
            base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            self.ollama_client = openai.OpenAI(base_url=f"{base_url}/v1", api_key="ollama")
            self.ollama_model = os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')
            logger.info(f"Initialized Ollama with model: {self.ollama_model} at {base_url}")

        else:
            raise ValueError(f"Unsupported provider: {self.provider}. Use 'openai', 'gemini', or 'ollama'.")

    def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM and return raw text response."""
        if self.provider == 'gemini':
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=self._genai.types.GenerationConfig(
                    temperature=0.0,
                    max_output_tokens=2000,
                )
            )
            return response.text.strip()

        elif self.provider == 'openai':
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a real estate data extraction specialist for Uzbekistan. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=2000,
            )
            return response.choices[0].message.content.strip()

        elif self.provider == 'ollama':
            response = self.ollama_client.chat.completions.create(
                model=self.ollama_model,
                messages=[
                    {"role": "system", "content": "You are a real estate data extraction specialist for Uzbekistan. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=2000,
            )
            return response.choices[0].message.content.strip()

    def extract(self, markdown: str, listing_id: str = None) -> Optional[Dict]:
        """Extract structured data from listing markdown"""
        prompt = self.EXTRACTION_PROMPT.format(markdown=markdown)

        try:
            content = self._call_llm(prompt)

            # Clean up markdown fences
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)
            data = self._normalize(data)

            if listing_id:
                data['olx_id'] = listing_id

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {self.provider} response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"{self.provider} extraction error: {e}")
            return None

    def _normalize(self, data: Dict) -> Dict:
        """Normalize extracted data"""

        # Normalize currency
        if 'currency' in data:
            curr = str(data['currency']).upper()
            if curr in ['$', 'USD', 'У.Е.', 'Y.E.', 'DOLLAR']:
                data['currency'] = 'USD'
            elif curr in ['UZS', "SO'M", 'СУМ', 'SUM']:
                data['currency'] = 'UZS'

        # Ensure numeric fields
        for field in ['price', 'rooms', 'floor', 'total_floors']:
            if field in data and data[field] is not None:
                try:
                    data[field] = int(float(str(data[field]).replace(',', '').replace(' ', '')))
                except (ValueError, TypeError):
                    data[field] = None

        if 'area_sqm' in data and data['area_sqm'] is not None:
            try:
                data['area_sqm'] = float(str(data['area_sqm']).replace(',', '.'))
            except (ValueError, TypeError):
                data['area_sqm'] = None

        # Normalize phone
        if 'contact_phone' in data and data['contact_phone']:
            phone = re.sub(r'[^\d]', '', str(data['contact_phone']))
            if len(phone) == 9:
                phone = '998' + phone
            if len(phone) == 12 and phone.startswith('998'):
                data['contact_phone'] = '+' + phone

        # Ensure amenities is a list
        if 'amenities' not in data or data['amenities'] is None:
            data['amenities'] = []

        return data


class OLXCrawlerN8N:
    """
    Playwright-based crawler for OLX.uz - outputs JSON array for n8n
    """

    def __init__(self, headless: bool = HEADLESS, output_file: str = "olx_listings.json",
                 provider: str = None):
        self.headless = headless
        self.output_file = Path(__file__).parent / output_file
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Initialize LLM extractor
        self.extractor = ListingExtractor(provider=provider)

        # All extracted listings
        self.listings: List[Dict] = []

        # Track processed IDs
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
        }

    def _extract_listing_id(self, url: str) -> Optional[str]:
        """Extract listing ID from OLX URL"""
        match = re.search(r'-(ID[a-zA-Z0-9]+)\.html', url)
        if match:
            return match.group(1)
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
                await self.page.goto(current_url, wait_until='networkidle')
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
            result = await self.crawl_listing(url)
            if result:
                listing_data, _ = result
                if listing_data:
                    self.listings.append(listing_data)

    async def init_browser(self):
        """Initialize Playwright browser"""
        logger.info("Initializing browser...")

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
        self.page.set_default_timeout(REQUEST_TIMEOUT)

        logger.info("Browser initialized")

    async def close_browser(self):
        """Close browser"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def get_listing_urls(self, category_url: str) -> List[str]:
        """Get all listing URLs from a category page"""
        logger.info(f"Collecting URLs from: {category_url}")

        try:
            await self.page.goto(category_url, wait_until='networkidle')
            await asyncio.sleep(DELAY_BETWEEN_REQUESTS)

            await self.page.wait_for_selector(
                CATEGORY_SELECTORS['listing_cards'],
                timeout=10000
            )

            links = await self.page.query_selector_all(CATEGORY_SELECTORS['listing_link'])

            urls = []
            seen = set()

            for link in links:
                href = await link.get_attribute('href')
                if href:
                    full_url = urljoin(OLX_BASE_URL, href)
                    if '/d/obyavlenie/' in full_url and full_url not in seen:
                        seen.add(full_url)
                        urls.append(full_url)

            logger.info(f"Found {len(urls)} listings")
            return urls

        except Exception as e:
            logger.error(f"Error collecting URLs: {e}")
            return []

    async def crawl_listing(self, listing_url: str) -> Optional[tuple]:
        """Crawl a single listing and extract data.

        Returns (extracted_data, seller_profile_url) or None.
        """
        listing_id = self._extract_listing_id(listing_url)

        if not listing_id:
            logger.warning(f"Could not extract ID from: {listing_url}")
            return None

        if listing_id in self.processed_ids:
            self.stats['duplicates_skipped'] += 1
            return None

        logger.info(f"Crawling: {listing_id}")

        try:
            await self.page.goto(listing_url, wait_until='networkidle')
            await asyncio.sleep(DELAY_BETWEEN_LISTINGS)

            html = await self.page.content()

            # Extract seller profile URL before converting to markdown
            seller_profile_url = self.get_seller_profile_url(html)

            markdown, raw_data = html_to_listing_markdown(html)

            if not markdown or len(markdown) < 50:
                logger.warning(f"Insufficient content for {listing_id}")
                self.stats['listings_failed'] += 1
                return None

            # Extract with Gemini
            extracted = self.extractor.extract(markdown, listing_id)

            if not extracted:
                logger.warning(f"Extraction failed for {listing_id}")
                self.stats['listings_failed'] += 1
                return None

            # Add metadata
            extracted['olx_id'] = listing_id
            extracted['url'] = listing_url
            extracted['images'] = raw_data.get('images', [])
            extracted['crawled_at'] = datetime.now().isoformat()
            extracted['source'] = 'olx_uz'

            self.processed_ids.add(listing_id)
            self.stats['listings_processed'] += 1

            logger.info(f"Extracted: {listing_id} - {extracted.get('property_type', 'unknown')}")
            return extracted, seller_profile_url

        except Exception as e:
            logger.error(f"Error crawling {listing_url}: {e}")
            self.stats['listings_failed'] += 1
            return None

    async def crawl_category(self, category_path: str, max_pages: int):
        """Crawl all listings in a category"""
        category_url = urljoin(OLX_BASE_URL, category_path)
        logger.info(f"Starting crawl: {category_url}")

        for page_num in range(1, max_pages + 1):
            logger.info(f"=== Page {page_num}/{max_pages} ===")

            if page_num == 1:
                current_url = category_url
            else:
                current_url = f"{category_url}?page={page_num}"

            listing_urls = await self.get_listing_urls(current_url)
            self.stats['listings_found'] += len(listing_urls)
            self.stats['pages_crawled'] += 1

            if not listing_urls:
                logger.info("No more listings found")
                break

            for url in listing_urls:
                result = await self.crawl_listing(url)
                if result:
                    listing_data, seller_profile_url = result
                    if listing_data:
                        self.listings.append(listing_data)

                    # Crawl seller's other real estate listings
                    if seller_profile_url and seller_profile_url not in self.visited_sellers:
                        await self.crawl_seller_profile(seller_profile_url)

            # Check for next page
            try:
                next_btn = await self.page.query_selector(CATEGORY_SELECTORS['next_page'])
                if not next_btn:
                    logger.info("No next page")
                    break
            except:
                break

    def save_output(self):
        """Save all listings to JSON file"""
        output = {
            "generated_at": datetime.now().isoformat(),
            "total_listings": len(self.listings),
            "stats": self.stats,
            "listings": self.listings
        }

        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(self.listings)} listings to {self.output_file}")

    async def run(self, category: str = "all_real_estate", max_pages: int = MAX_PAGES_PER_CATEGORY):
        """Main entry point"""
        logger.info("=" * 60)
        logger.info(f"OLX.uz Crawler for n8n (provider: {self.extractor.provider})")
        logger.info(f"Category: {category}")
        logger.info(f"Max pages: {max_pages}")
        logger.info(f"Output: {self.output_file}")
        logger.info("=" * 60)

        try:
            await self.init_browser()

            category_path = CATEGORIES.get(category)
            if not category_path:
                logger.error(f"Unknown category: {category}")
                logger.info(f"Available: {list(CATEGORIES.keys())}")
                return

            await self.crawl_category(category_path, max_pages)

        except Exception as e:
            logger.error(f"Crawler error: {e}")
            raise

        finally:
            await self.close_browser()
            self.save_output()
            self._print_stats()

    def _print_stats(self):
        """Print statistics"""
        logger.info("\n" + "=" * 60)
        logger.info("CRAWL COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Pages crawled:          {self.stats['pages_crawled']}")
        logger.info(f"Listings found:         {self.stats['listings_found']}")
        logger.info(f"Listings processed:     {self.stats['listings_processed']}")
        logger.info(f"Listings failed:        {self.stats['listings_failed']}")
        logger.info(f"Duplicates skipped:     {self.stats['duplicates_skipped']}")
        logger.info(f"Seller profiles visited:{self.stats['seller_profiles_visited']}")
        logger.info(f"Seller listings found:  {self.stats['seller_listings_found']}")
        logger.info(f"Output file:            {self.output_file}")
        logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='OLX.uz Crawler for n8n')

    parser.add_argument(
        '--provider',
        type=str,
        default=None,
        choices=['openai', 'gemini', 'ollama'],
        help='LLM provider to use (default: LLM_PROVIDER from .env, or gemini)'
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
        help='Maximum pages to crawl'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='olx_listings.json',
        help='Output JSON file name'
    )

    parser.add_argument(
        '--headless',
        type=str,
        default='true',
        choices=['true', 'false'],
        help='Run browser in headless mode'
    )

    args = parser.parse_args()

    headless = args.headless.lower() == 'true'

    crawler = OLXCrawlerN8N(headless=headless, output_file=args.output, provider=args.provider)
    asyncio.run(crawler.run(category=args.category, max_pages=args.max_pages))


if __name__ == '__main__':
    main()
