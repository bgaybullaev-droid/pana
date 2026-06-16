"""
Telegram Web Scraper
Scrapes public Telegram channel posts without authentication using web preview URLs.
Works with https://t.me/s/{channel} pages.
"""

import re
import os
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin


@dataclass
class TelegramMessage:
    """Represents a scraped Telegram message"""
    channel: str
    message_id: int
    text: str
    timestamp: Optional[datetime] = None
    image_urls: List[str] = field(default_factory=list)
    views: Optional[int] = None
    forwarded_from: Optional[str] = None

    def __post_init__(self):
        if self.image_urls is None:
            self.image_urls = []


class TelegramHTMLParser(HTMLParser):
    """Parser for Telegram web preview HTML"""

    def __init__(self):
        super().__init__()
        self.messages: List[TelegramMessage] = []

        # State tracking
        self.in_message = False
        self.in_text = False
        self.in_forwarded = False
        self.current_message: Optional[Dict] = None
        self.current_text_parts: List[str] = []
        self.depth = 0
        self.text_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get('class', '')

        # Start of a message
        if 'data-post' in attrs_dict:
            self.in_message = True
            self.depth = 1
            post_id = attrs_dict['data-post']
            channel, msg_id = post_id.rsplit('/', 1)
            self.current_message = {
                'channel': channel,
                'message_id': int(msg_id),
                'text': '',
                'image_urls': [],
                'timestamp': None,
                'views': None,
                'forwarded_from': None
            }
            return

        if not self.in_message:
            return

        self.depth += 1

        # Text content
        if 'tgme_widget_message_text' in class_name:
            self.in_text = True
            self.text_depth = self.depth
            self.current_text_parts = []

        # Forwarded from
        if 'tgme_widget_message_forwarded_from_name' in class_name:
            self.in_forwarded = True

        # Image URLs from style attribute
        if 'tgme_widget_message_photo' in class_name:
            style = attrs_dict.get('style', '')
            match = re.search(r"url\(['\"]?(https?://[^'\")\s]+)['\"]?\)", style)
            if match and self.current_message:
                self.current_message['image_urls'].append(match.group(1))

        # Video thumbnail (fallback)
        if tag == 'video' and 'poster' in attrs_dict:
            if self.current_message:
                self.current_message['image_urls'].append(attrs_dict['poster'])

        # Timestamp from time tag
        if tag == 'time' and 'datetime' in attrs_dict:
            if self.current_message:
                try:
                    dt_str = attrs_dict['datetime']
                    self.current_message['timestamp'] = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                except ValueError:
                    pass

        # Views count
        if 'tgme_widget_message_views' in class_name:
            pass  # Will capture in handle_data

    def handle_endtag(self, tag):
        if not self.in_message:
            return

        self.depth -= 1

        # End of text section
        if self.in_text and self.depth < self.text_depth:
            self.in_text = False
            if self.current_message and self.current_text_parts:
                # Append text (handles multiple text blocks in forwarded messages)
                if self.current_message['text']:
                    self.current_message['text'] += '\n' + ''.join(self.current_text_parts)
                else:
                    self.current_message['text'] = ''.join(self.current_text_parts)
                self.current_text_parts = []

        # End of message
        if self.depth <= 0 and self.current_message:
            # Only add if has text or images
            if self.current_message['text'] or self.current_message['image_urls']:
                msg = TelegramMessage(
                    channel=self.current_message['channel'],
                    message_id=self.current_message['message_id'],
                    text=self.current_message['text'].strip(),
                    timestamp=self.current_message['timestamp'],
                    image_urls=self.current_message['image_urls'],
                    views=self.current_message['views'],
                    forwarded_from=self.current_message['forwarded_from']
                )
                self.messages.append(msg)

            self.in_message = False
            self.current_message = None

    def handle_data(self, data):
        if self.in_text:
            self.current_text_parts.append(data)
        elif self.in_forwarded and self.current_message:
            self.current_message['forwarded_from'] = data.strip()
            self.in_forwarded = False


class TelegramWebScraper:
    """Scraper for public Telegram channels via web preview"""

    BASE_URL = "https://t.me/s/"

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).parent / 'output'
        self.images_dir = self.output_dir / 'images'
        self.images_dir.mkdir(parents=True, exist_ok=True)

        # Rate limiting
        self.request_delay = 1.0  # seconds between requests
        self.last_request_time = 0

    async def _rate_limit(self):
        """Ensure minimum delay between requests"""
        import time
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            await asyncio.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()

    async def fetch_channel_messages(
        self,
        channel_username: str,
        limit: int = 20,
        before_id: Optional[int] = None,
        session: Optional[aiohttp.ClientSession] = None
    ) -> List[TelegramMessage]:
        """
        Fetch messages from a public Telegram channel.

        Args:
            channel_username: Channel username (without @)
            limit: Maximum number of messages to fetch
            before_id: Fetch messages before this ID (for pagination)
            session: Optional aiohttp session to reuse

        Returns:
            List of TelegramMessage objects
        """
        messages = []
        close_session = False

        if session is None:
            session = aiohttp.ClientSession(
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
            )
            close_session = True

        try:
            url = f"{self.BASE_URL}{channel_username}"
            if before_id:
                url += f"?before={before_id}"

            await self._rate_limit()

            async with session.get(url) as response:
                if response.status != 200:
                    print(f"[ERROR] Failed to fetch {url}: HTTP {response.status}")
                    return []

                html = await response.text()

            # Parse HTML
            parser = TelegramHTMLParser()
            parser.feed(html)
            messages = parser.messages

            # Messages come in reverse order (newest first), reverse if needed
            messages.reverse()

            # Pagination: fetch more if needed
            while len(messages) < limit and messages:
                oldest_id = messages[0].message_id
                await self._rate_limit()

                url = f"{self.BASE_URL}{channel_username}?before={oldest_id}"
                async with session.get(url) as response:
                    if response.status != 200:
                        break
                    html = await response.text()

                parser = TelegramHTMLParser()
                parser.feed(html)
                new_messages = parser.messages

                if not new_messages:
                    break

                new_messages.reverse()
                messages = new_messages + messages

            # Return only requested limit
            return messages[-limit:] if len(messages) > limit else messages

        finally:
            if close_session:
                await session.close()

    async def download_image(
        self,
        image_url: str,
        listing_id: int,
        image_index: int,
        session: Optional[aiohttp.ClientSession] = None
    ) -> Optional[str]:
        """
        Download an image and save it locally.

        Args:
            image_url: URL of the image to download
            listing_id: ID for naming the file
            image_index: Index of the image (for multiple images)
            session: Optional aiohttp session to reuse

        Returns:
            Relative path to saved image, or None on failure
        """
        close_session = False

        if session is None:
            session = aiohttp.ClientSession(
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            close_session = True

        try:
            await self._rate_limit()

            async with session.get(image_url) as response:
                if response.status != 200:
                    print(f"[ERROR] Failed to download image: HTTP {response.status}")
                    return None

                # Determine file extension
                content_type = response.headers.get('Content-Type', 'image/jpeg')
                if 'png' in content_type:
                    ext = '.png'
                elif 'gif' in content_type:
                    ext = '.gif'
                elif 'webp' in content_type:
                    ext = '.webp'
                else:
                    ext = '.jpg'

                # Create filename
                filename = f"listing_{listing_id:05d}_img_{image_index}{ext}"
                filepath = self.images_dir / filename

                # Download and save
                content = await response.read()
                with open(filepath, 'wb') as f:
                    f.write(content)

                # Return relative path
                return f"images/{filename}"

        except Exception as e:
            print(f"[ERROR] Failed to download image: {e}")
            return None
        finally:
            if close_session:
                await session.close()

    async def scrape_channel(
        self,
        channel_username: str,
        limit: int = 20,
        download_images: bool = True,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape a channel and return structured data.

        Args:
            channel_username: Channel username (without @)
            limit: Maximum messages to scrape
            download_images: Whether to download images locally
            progress_callback: Optional callback(message: str) for progress updates

        Returns:
            List of dictionaries with message data
        """
        def log(msg: str):
            if progress_callback:
                progress_callback(msg)
            else:
                print(msg)

        log(f"Fetching messages from @{channel_username}...")

        async with aiohttp.ClientSession(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        ) as session:
            messages = await self.fetch_channel_messages(
                channel_username,
                limit=limit,
                session=session
            )

            log(f"Found {len(messages)} messages")

            results = []
            for i, msg in enumerate(messages):
                result = {
                    'channel': msg.channel,
                    'message_id': msg.message_id,
                    'text': msg.text,
                    'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                    'image_urls': msg.image_urls,
                    'local_images': [],
                    'forwarded_from': msg.forwarded_from
                }

                # Download images if requested
                if download_images and msg.image_urls:
                    listing_id = i + 1  # Temporary ID, will be assigned properly by CSV exporter
                    for j, url in enumerate(msg.image_urls, 1):
                        local_path = await self.download_image(
                            url,
                            listing_id,
                            j,
                            session=session
                        )
                        if local_path:
                            result['local_images'].append(local_path)

                    if result['local_images']:
                        log(f"Downloaded {len(result['local_images'])} images for message {msg.message_id}")

                results.append(result)

            return results


# Convenience functions for command-line usage
async def test_scraper():
    """Test the scraper with a sample channel"""
    scraper = TelegramWebScraper()

    # Test channels from the schema
    test_channels = ['NAMANGAN_UYJOY_BOZORI', 'baburieltor']

    for channel in test_channels:
        print(f"\n{'='*60}")
        print(f"Testing channel: @{channel}")
        print('='*60)

        messages = await scraper.fetch_channel_messages(channel, limit=5)

        for msg in messages:
            print(f"\n--- Message {msg.message_id} ---")
            print(f"Timestamp: {msg.timestamp}")
            print(f"Images: {len(msg.image_urls)}")
            print(f"Text preview: {msg.text[:200]}..." if len(msg.text) > 200 else f"Text: {msg.text}")
            if msg.forwarded_from:
                print(f"Forwarded from: {msg.forwarded_from}")


if __name__ == '__main__':
    asyncio.run(test_scraper())
