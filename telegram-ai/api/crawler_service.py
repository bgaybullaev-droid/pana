"""
Crawler Service Module
Manages background crawl jobs for CSV export
Uses web scraping to fetch public Telegram channel posts (no authentication required)
"""

import asyncio
import threading
import uuid
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

import yaml

# Add crawler directory to path
CRAWLER_DIR = Path(__file__).parent.parent / 'crawler'
sys.path.insert(0, str(CRAWLER_DIR))


class CrawlJob:
    """Represents a single crawl job"""

    def __init__(self, job_id: str, channels: List[str], messages_per_channel: int):
        self.job_id = job_id
        self.channels = channels
        self.messages_per_channel = messages_per_channel
        self.status = 'pending'  # pending, running, completed, failed, stopped
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None

        # Progress tracking
        self.current_channel: Optional[str] = None
        self.current_channel_index: int = 0
        self.total_channels: int = len(channels)

        # Statistics
        self.stats = {
            'total_processed': 0,
            'total_success': 0,
            'total_failed': 0,
            'total_skipped': 0,
            'total_images': 0,
            'channels_processed': 0,
            'channels_failed': 0
        }

        # Output paths
        self.output_dir = str(CRAWLER_DIR / 'output')
        self.csv_path: Optional[str] = None

        # Log messages
        self.logs: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for JSON response"""
        return {
            'job_id': self.job_id,
            'status': self.status,
            'channels': self.channels,
            'messages_per_channel': self.messages_per_channel,
            'current_channel': self.current_channel,
            'current_channel_index': self.current_channel_index,
            'total_channels': self.total_channels,
            'progress_percent': int((self.current_channel_index / self.total_channels) * 100) if self.total_channels > 0 else 0,
            'stats': self.stats,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error': self.error,
            'output_dir': self.output_dir,
            'csv_path': self.csv_path,
            'recent_logs': self.logs[-20:]  # Last 20 log entries
        }

    def add_log(self, message: str):
        """Add a log message"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.logs.append(f"[{timestamp}] {message}")
        # Keep only last 100 logs
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]


class CrawlerService:
    """Service to manage crawler jobs"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.jobs: Dict[str, CrawlJob] = {}
        self.current_job: Optional[CrawlJob] = None
        self._stop_requested = False
        self._crawler_thread: Optional[threading.Thread] = None
        self._initialized = True

    def get_available_channels(self) -> List[Dict[str, Any]]:
        """Get list of available channels from schemas"""
        channels = []
        schemas_dir = CRAWLER_DIR / 'schemas'

        if not schemas_dir.exists():
            return channels

        for schema_file in schemas_dir.glob('*.yaml'):
            try:
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema = yaml.safe_load(f)

                schema_name = schema.get('schema_name', schema_file.stem)
                schema_channels = schema.get('channels', [])

                for ch in schema_channels:
                    channels.append({
                        'username': ch,
                        'schema': schema_name,
                        'schema_file': schema_file.name
                    })
            except Exception as e:
                print(f"Error loading schema {schema_file}: {e}")

        return channels

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get list of available schemas"""
        schemas = []
        schemas_dir = CRAWLER_DIR / 'schemas'

        if not schemas_dir.exists():
            return schemas

        for schema_file in schemas_dir.glob('*.yaml'):
            try:
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema = yaml.safe_load(f)

                schemas.append({
                    'name': schema.get('schema_name', schema_file.stem),
                    'file': schema_file.name,
                    'description': schema.get('description', ''),
                    'channels': schema.get('channels', []),
                    'channel_count': len(schema.get('channels', []))
                })
            except Exception as e:
                print(f"Error loading schema {schema_file}: {e}")

        return schemas

    def is_running(self) -> bool:
        """Check if a crawl job is currently running"""
        return self.current_job is not None and self.current_job.status == 'running'

    def start_crawl(
        self,
        channels: Optional[List[str]] = None,
        messages_per_channel: int = 10
    ) -> CrawlJob:
        """
        Start a new crawl job

        Args:
            channels: List of channel usernames (None = all from schema)
            messages_per_channel: Number of messages to fetch per channel

        Returns:
            CrawlJob instance
        """
        if self.is_running():
            raise RuntimeError("A crawl job is already running")

        # Get channels from schema if not specified
        if not channels:
            available = self.get_available_channels()
            channels = [ch['username'] for ch in available]

        if not channels:
            raise ValueError("No channels to crawl")

        # Create job
        job_id = str(uuid.uuid4())[:8]
        job = CrawlJob(job_id, channels, messages_per_channel)
        self.jobs[job_id] = job
        self.current_job = job
        self._stop_requested = False

        # Start crawler in background thread
        self._crawler_thread = threading.Thread(
            target=self._run_crawler,
            args=(job,),
            daemon=True
        )
        self._crawler_thread.start()

        return job

    def stop_crawl(self) -> bool:
        """Request to stop the current crawl"""
        if not self.is_running():
            return False

        self._stop_requested = True
        if self.current_job:
            self.current_job.add_log("Stop requested by user")
        return True

    def get_job(self, job_id: str) -> Optional[CrawlJob]:
        """Get job by ID"""
        return self.jobs.get(job_id)

    def get_current_job(self) -> Optional[CrawlJob]:
        """Get the current/most recent job"""
        return self.current_job

    def get_all_jobs(self) -> List[CrawlJob]:
        """Get all jobs"""
        return list(self.jobs.values())

    def _run_crawler(self, job: CrawlJob):
        """Run the crawler in a background thread"""
        job.status = 'running'
        job.started_at = datetime.now()
        job.add_log(f"Starting crawl job {job.job_id}")
        job.add_log(f"Channels: {len(job.channels)}, Messages per channel: {job.messages_per_channel}")

        try:
            # Run async crawler
            asyncio.run(self._async_crawl(job))

            if self._stop_requested:
                job.status = 'stopped'
                job.add_log("Crawl stopped by user")
            else:
                job.status = 'completed'
                job.add_log("Crawl completed successfully")

        except Exception as e:
            job.status = 'failed'
            job.error = str(e)
            job.add_log(f"Crawl failed: {e}")
            import traceback
            traceback.print_exc()

        finally:
            job.completed_at = datetime.now()

    async def _async_crawl(self, job: CrawlJob):
        """Async crawler execution using web scraping (no Telegram auth required)"""
        # Import crawler modules
        try:
            from csv_exporter import CSVExporter
            from llm_extractor import LLMExtractor
            from telegram_web_scraper import TelegramWebScraper
            from backend_push import push_listing_with_images
        except ImportError as e:
            raise RuntimeError(f"Failed to import crawler modules: {e}")

        # Initialize components
        csv_exporter = CSVExporter(output_dir=job.output_dir)
        llm_extractor = LLMExtractor()
        scraper = TelegramWebScraper(output_dir=job.output_dir)

        job.csv_path = str(csv_exporter.csv_path)
        job.add_log(f"Output directory: {job.output_dir}")
        job.add_log(f"CSV file: {job.csv_path}")
        job.add_log("Using web scraping (no Telegram authentication required)")

        # Load schema
        schema_path = CRAWLER_DIR / 'schemas' / 'real_estate.yaml'
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = yaml.safe_load(f)

        try:
            # Process each channel
            for i, channel_username in enumerate(job.channels):
                if self._stop_requested:
                    break

                job.current_channel = channel_username
                job.current_channel_index = i
                job.add_log(f"Processing channel {i+1}/{len(job.channels)}: @{channel_username}")

                try:
                    # Fetch messages using web scraper
                    messages = await scraper.fetch_channel_messages(
                        channel_username,
                        limit=job.messages_per_channel
                    )

                    if not messages:
                        job.add_log(f"No messages found in @{channel_username}")
                        job.stats['channels_failed'] += 1
                        continue

                    job.add_log(f"Fetched {len(messages)} messages from @{channel_username}")

                    # Process each message
                    for msg in messages:
                        if self._stop_requested:
                            break

                        text = msg.text or ""
                        if len(text) < 5:
                            job.add_log(f"Skipped message {msg.message_id}: text too short ({len(text)} chars)")
                            job.stats['total_skipped'] += 1
                            continue

                        # Check duplicate
                        if csv_exporter.is_duplicate(channel_username, msg.message_id):
                            job.add_log(f"Skipped message {msg.message_id}: duplicate")
                            job.stats['total_skipped'] += 1
                            continue

                        job.stats['total_processed'] += 1

                        # Extract with LLM
                        try:
                            extracted_data = llm_extractor.extract(schema, text, channel=channel_username)
                            if not extracted_data:
                                job.add_log(f"LLM extraction returned empty for message {msg.message_id}")
                                job.stats['total_failed'] += 1
                                continue
                        except Exception as e:
                            job.add_log(f"LLM extraction failed: {e}")
                            job.stats['total_failed'] += 1
                            continue

                        # Get listing ID and download images
                        listing_id = csv_exporter.get_next_id()
                        image_paths = []

                        # Download images from web URLs
                        if msg.image_urls:
                            import aiohttp
                            async with aiohttp.ClientSession(
                                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                            ) as session:
                                for idx, img_url in enumerate(msg.image_urls, 1):
                                    try:
                                        local_path = await scraper.download_image(
                                            img_url,
                                            listing_id,
                                            idx,
                                            session=session
                                        )
                                        if local_path:
                                            image_paths.append(local_path)
                                            job.stats['total_images'] += 1
                                    except Exception as e:
                                        job.add_log(f"Image download failed: {e}")

                        # Save to CSV
                        csv_exporter.save_row(
                            listing_id=listing_id,
                            channel=channel_username,
                            message_id=msg.message_id,
                            timestamp=msg.timestamp,
                            extracted_data=extracted_data,
                            image_paths=image_paths,
                            raw_text=text
                        )

                        # Push to Real Estate backend (images + listing)
                        if image_paths:
                            try:
                                # Convert relative paths to absolute
                                abs_image_paths = [
                                    os.path.join(job.output_dir, p) for p in image_paths
                                ]
                                result = push_listing_with_images(
                                    extracted_data=extracted_data,
                                    channel=channel_username,
                                    message_id=msg.message_id,
                                    raw_text=text,
                                    image_paths=abs_image_paths,
                                )
                                if result and result.get('created', 0) > 0:
                                    job.add_log(f"Pushed to backend: listing #{listing_id}")
                                elif result and result.get('duplicates', 0) > 0:
                                    job.add_log(f"Backend: duplicate listing #{listing_id}")
                            except Exception as e:
                                job.add_log(f"Backend push failed: {e}")

                        job.stats['total_success'] += 1
                        price = extracted_data.get('price', 'N/A')
                        rooms = extracted_data.get('rooms', 'N/A')
                        job.add_log(f"Saved listing #{listing_id}: {rooms} rooms, ${price}")

                        await asyncio.sleep(0.5)  # Rate limit

                    job.stats['channels_processed'] += 1

                except Exception as e:
                    job.add_log(f"Error processing @{channel_username}: {e}")
                    import traceback
                    traceback.print_exc()
                    job.stats['channels_failed'] += 1

                await asyncio.sleep(1)  # Delay between channels

        finally:
            job.current_channel_index = len(job.channels)

        # Final stats
        job.add_log(f"Channels: {job.stats['channels_processed']}/{len(job.channels)}")
        job.add_log(f"Success: {job.stats['total_success']}, Failed: {job.stats['total_failed']}")
        job.add_log(f"Images: {job.stats['total_images']}")

    def get_csv_path(self) -> Optional[str]:
        """Get path to current CSV file"""
        csv_path = CRAWLER_DIR / 'output' / 'real_estate_listings.csv'
        if csv_path.exists():
            return str(csv_path)
        return None

    def get_output_stats(self) -> Dict[str, Any]:
        """Get statistics about output files"""
        output_dir = CRAWLER_DIR / 'output'
        images_dir = output_dir / 'images'
        csv_path = output_dir / 'real_estate_listings.csv'

        stats = {
            'csv_exists': csv_path.exists(),
            'csv_path': str(csv_path) if csv_path.exists() else None,
            'csv_size': csv_path.stat().st_size if csv_path.exists() else 0,
            'images_count': 0,
            'images_size': 0
        }

        if images_dir.exists():
            images = list(images_dir.glob('*.jpg'))
            stats['images_count'] = len(images)
            stats['images_size'] = sum(img.stat().st_size for img in images)

        return stats


# Global service instance
crawler_service = CrawlerService()
