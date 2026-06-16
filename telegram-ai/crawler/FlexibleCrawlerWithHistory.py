#!/usr/bin/env python3
"""
Flexible Telegram Crawler with Historical Message Processing
Processes past messages on startup, then monitors new messages in real-time
"""

import asyncio
import os
import time
import yaml
import requests
from pathlib import Path
from typing import Dict
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

# Import configurations
try:
    from config import api_id, api_hash, phone_number, session_name
except ImportError:
    print("[ERROR] config.py not found!")
    print("Please create crawler/config.py with your Telegram credentials.")
    exit(1)

from llm_config import PROCESS_HISTORICAL_MESSAGES

# API endpoints (legacy dashboard API — optional, can be disabled)
API_BASE_URL = os.getenv('LEGACY_API_URL', 'http://localhost:5000/api/Crawler')
API_LISTING_IMAGES = f'{API_BASE_URL}/listing/images'
LEGACY_API_ENABLED = os.getenv('LEGACY_API_ENABLED', 'false').lower() == 'true'

# Load schema loader
try:
    from schema_loader import SchemaLoader
    from llm_extractor import LLMExtractor
    from image_embeddings import ImageEmbedder
    from vector_db import VectorDatabase
    from backend_push import push_listing_with_images
except ImportError as e:
    print(f"[ERROR] Missing modules: {e}")
    print("Please ensure all required modules are in the crawler directory.")
    exit(1)


class ChannelTokenBucket:
    """Per-channel token-bucket rate limiter for Telethon calls.

    Block A V2.0 (A8) — when Telegram throttles us (``FloodWaitError``),
    we don't want to keep hammering every channel equally. Each channel
    has its own bucket of N tokens that refill at ``base_rate`` per
    second. On a FloodWait the bucket's effective capacity is reduced
    (``shrink_on_floodwait``) so subsequent iterations naturally slow
    that one channel down without affecting the others.

    Lightweight: in-memory only, single-process. The crawler runs as a
    singleton so we don't need a distributed bucket. Defaults of N=20
    per 60s ≈ Telethon's safe range for read calls; the per-channel
    sleep after a FloodWait obeys the exact ``seconds`` Telegram asks for.
    """

    def __init__(self, capacity: int = 20, refill_seconds: float = 60.0):
        self._capacity_default = capacity
        self._refill_seconds = refill_seconds  # seconds to fully refill
        self._buckets: Dict[str, Dict[str, float]] = {}

    def _state(self, channel: str) -> Dict[str, float]:
        return self._buckets.setdefault(
            channel,
            {
                "capacity": float(self._capacity_default),
                "tokens": float(self._capacity_default),
                "last": time.monotonic(),
                "cooldown_until": 0.0,
            },
        )

    async def acquire(self, channel: str) -> None:
        """Wait until a token is available for ``channel``. Honours cooldown."""
        st = self._state(channel)
        now = time.monotonic()

        # Cooldown from a previous FloodWait: block until window passes.
        if st["cooldown_until"] > now:
            await asyncio.sleep(st["cooldown_until"] - now)
            now = time.monotonic()

        # Refill: tokens grow linearly toward ``capacity`` over ``refill_seconds``.
        elapsed = now - st["last"]
        refill = elapsed * (st["capacity"] / self._refill_seconds)
        st["tokens"] = min(st["capacity"], st["tokens"] + refill)
        st["last"] = now

        if st["tokens"] < 1.0:
            # Compute precise wait until next whole token, then deduct.
            need = 1.0 - st["tokens"]
            wait = need * (self._refill_seconds / max(st["capacity"], 1.0))
            await asyncio.sleep(wait)
            st["tokens"] = 0.0
            st["last"] = time.monotonic()
        else:
            st["tokens"] -= 1.0

    def shrink_on_floodwait(self, channel: str, seconds: int) -> None:
        """React to a FloodWait: drop bucket capacity, install a cooldown.

        Capacity is halved (floor 2) so the channel slows down on the
        next cycle. Cooldown is honoured before any further ``acquire``."""
        st = self._state(channel)
        st["capacity"] = max(2.0, st["capacity"] / 2.0)
        st["tokens"] = 0.0
        st["cooldown_until"] = time.monotonic() + max(1, int(seconds))

    def reset_channel(self, channel: str) -> None:
        """Restore a channel to default capacity (e.g. on next refresh)."""
        self._buckets[channel] = {
            "capacity": float(self._capacity_default),
            "tokens": float(self._capacity_default),
            "last": time.monotonic(),
            "cooldown_until": 0.0,
        }


class FlexibleCrawler:
    """Flexible crawler with historical message processing"""

    def __init__(self):
        self.client = TelegramClient(session_name, api_id, api_hash)
        self.schema_loader = SchemaLoader()
        self.llm_extractor = LLMExtractor()
        self.image_embedder = ImageEmbedder()
        self.vector_db = VectorDatabase()

        # Stats
        self.stats = {
            'historical_processed': 0,
            'historical_success': 0,
            'historical_failed': 0,
            'realtime_processed': 0,
            'realtime_success': 0,
            'realtime_failed': 0
        }

        # Block A V2.0 (A8) — per-channel deltas pending writeback to
        # the source_metric table. Flushed via :meth:`flush_metrics`
        # after each historical pass and every N realtime messages.
        self._metric_buffer: Dict[str, Dict[str, int]] = {}

        # Block A V2.0 (A8) — per-channel token-bucket rate limiter.
        # On FloodWait we shrink the bucket for the offending channel
        # instead of pausing the entire crawler, so well-behaved
        # channels keep flowing.
        rl_capacity = int(os.getenv("CRAWLER_RL_CAPACITY", "20"))
        rl_window = float(os.getenv("CRAWLER_RL_WINDOW_SECONDS", "60"))
        self.rate_limiter = ChannelTokenBucket(
            capacity=rl_capacity, refill_seconds=rl_window
        )

    # ── A8: per-source metric writeback ───────────────────────────────

    def _bump_metric(self, channel: str, **deltas) -> None:
        """Accumulate counters in-memory; flushed in batches."""
        bucket = self._metric_buffer.setdefault(
            channel,
            {"parsed": 0, "saved": 0, "failed": 0, "duplicates": 0, "ai_failed": 0, "notified": 0},
        )
        for k, v in deltas.items():
            if k in bucket and v:
                bucket[k] += v

    def flush_metrics(self) -> None:
        """Push accumulated counters to ``source_metric`` via db_sources."""
        if not self._metric_buffer:
            return
        try:
            from db_sources import find_source_id, write_source_metric
        except ImportError:
            self.log("db_sources unavailable; metric flush skipped", "WARNING")
            self._metric_buffer.clear()
            return

        flushed = 0
        for channel, deltas in self._metric_buffer.items():
            sid = find_source_id(channel)
            if not sid:
                continue
            ok = write_source_metric(sid, **deltas)
            if ok:
                flushed += 1
        self.log(f"flushed metrics for {flushed} sources")
        self._metric_buffer.clear()

    def log(self, message, level='INFO'):
        """Log message with level"""
        print(f"[{level}] {message}")

    async def process_message(self, message, is_historical=False):
        """Process a single message"""
        try:
            # Get channel username
            if hasattr(message.peer_id, 'channel_id'):
                channel = await self.client.get_entity(message.peer_id)
                username = channel.username if hasattr(channel, 'username') else str(channel.id)
            else:
                return False

            # Get schema for this channel
            schema = self.schema_loader.get_schema_for_channel(username)
            if not schema:
                self.log(f"No schema for channel @{username}, skipping", 'DEBUG')
                return False

            # Check if message has text
            text = message.message or ""
            if not text or len(text) < 10:
                self.log(f"Message too short, skipping", 'DEBUG')
                return False

            # Check if message has photo (single or album)
            has_photo = isinstance(message.media, MessageMediaPhoto)
            if not has_photo:
                self.log(f"No photo in message, skipping", 'DEBUG')
                return False

            # Collect all photos: check if this is part of a grouped album
            album_messages = []
            if message.grouped_id:
                # Fetch all messages in the album group
                channel_entity = await self.client.get_entity(message.peer_id)
                async for msg in self.client.iter_messages(channel_entity, limit=20, min_id=message.id - 10, max_id=message.id + 10):
                    if msg.grouped_id == message.grouped_id and isinstance(msg.media, MessageMediaPhoto):
                        album_messages.append(msg)
                # Sort by message ID to maintain order
                album_messages.sort(key=lambda m: m.id)
            else:
                album_messages = [message]

            # Extract data using LLM
            self.log(f"{'[HISTORICAL]' if is_historical else '[REALTIME]'} Extracting from @{username} message {message.id}...")

            extracted_data = self.llm_extractor.extract(schema, text, channel=username)
            if not extracted_data:
                self.log(f"Extraction failed for message {message.id}", 'WARNING')
                return False

            self.log(f"Extracted: {extracted_data.get('title', 'N/A')[:50]}...")

            # Generate text embedding
            text_embedding = self.vector_db.generate_text_embedding(text)

            # Check for text duplicates
            text_duplicates = self.vector_db.search_similar_text(
                text_embedding,
                top_k=3,
                threshold=0.92
            )

            # POST to legacy API (optional — dashboard)
            listing_id = message.id  # fallback ID
            if LEGACY_API_ENABLED:
                post_data = {
                    'schema_type': schema['schema_name'],
                    'channel_username': username,
                    'message_id': message.id,
                    'raw_data': text,
                    'extracted_data': extracted_data,
                    'text_embedding': text_embedding.tolist() if hasattr(text_embedding, 'tolist') else text_embedding,
                    'duplicate_info': {
                        'is_duplicate': len(text_duplicates) > 0,
                        'duplicate_of': text_duplicates[0]['id'] if text_duplicates else None,
                        'similarity_score': text_duplicates[0]['similarity'] if text_duplicates else 0.0
                    }
                }
                try:
                    response = requests.post(API_BASE_URL, json=post_data, timeout=30)
                    if response.status_code == 201:
                        listing_id = response.json().get('id', listing_id)
                        self.log(f"Legacy API: created listing #{listing_id}")
                    else:
                        self.log(f"Legacy API error: {response.status_code}", 'WARNING')
                except Exception as e:
                    self.log(f"Legacy API unavailable: {e}", 'WARNING')

            # Store text embedding in vector DB
            self.vector_db.add_text_embedding(
                listing_id=listing_id,
                embedding=text_embedding,
                text_preview=text[:100],
                metadata={
                    'channel': username,
                    'message_id': message.id,
                    'schema': schema['schema_name']
                }
            )

            # Download images (supports albums) — keep temp files for backend push
            downloaded_paths = []
            for img_idx, album_msg in enumerate(album_messages):
                photo_path = f"temp_{listing_id}_{img_idx}.jpg"
                try:
                    await self.client.download_media(album_msg.media, photo_path)

                    if os.path.exists(photo_path):
                        downloaded_paths.append(photo_path)

                    # Generate image embedding
                    image_embedding = self.image_embedder.embed_image(photo_path)
                    if image_embedding is None:
                        self.log(f"Image embedding failed for image {img_idx}", 'WARNING')
                        continue

                    # Check for image duplicates
                    image_duplicates = self.vector_db.search_similar_images(
                        image_embedding,
                        top_k=3,
                        threshold=0.88
                    )

                    # Upload to legacy API (optional)
                    if LEGACY_API_ENABLED:
                        try:
                            with open(photo_path, 'rb') as f:
                                files = {'ListingImages': f}
                                data = {
                                    'listingId': listing_id,
                                    'image_embedding': image_embedding.tolist() if hasattr(image_embedding, 'tolist') else image_embedding,
                                    'duplicate_info': {
                                        'is_duplicate': len(image_duplicates) > 0,
                                        'duplicate_of': image_duplicates[0]['id'] if image_duplicates else None,
                                        'similarity_score': image_duplicates[0]['similarity'] if image_duplicates else 0.0
                                    }
                                }
                                img_response = requests.post(API_LISTING_IMAGES, files=files, data=data, timeout=30)
                            if img_response.status_code == 201:
                                image_id = img_response.json().get('id')
                                self.vector_db.add_image_embedding(
                                    listing_id=listing_id,
                                    image_id=image_id,
                                    embedding=image_embedding,
                                    metadata={
                                        'channel': username,
                                        'message_id': album_msg.id
                                    }
                                )
                        except Exception as e:
                            self.log(f"Legacy image upload failed: {e}", 'WARNING')

                except Exception as e:
                    self.log(f"Image download error: {e}", 'WARNING')

            # ── Push to Real Estate backend (primary) ──
            if downloaded_paths:
                push_listing_with_images(
                    extracted_data=extracted_data,
                    channel=username,
                    message_id=message.id,
                    raw_text=text,
                    image_paths=downloaded_paths,
                )
                self.log(f"Pushed to backend with {len(downloaded_paths)} images")
            else:
                self.log("No images downloaded — skipping backend push", 'WARNING')

            # Clean up temp files
            for path in downloaded_paths:
                if os.path.exists(path):
                    os.remove(path)

            return len(downloaded_paths) > 0

        except Exception as e:
            self.log(f"Error processing message: {e}", 'ERROR')
            import traceback
            traceback.print_exc()
            return False

    async def process_historical_messages(self):
        """Process historical messages from all configured channels"""
        if PROCESS_HISTORICAL_MESSAGES <= 0:
            self.log("Historical message processing disabled (PROCESS_HISTORICAL_MESSAGES=0)")
            return

        self.log(f"\n{'='*60}")
        self.log(f"Processing {PROCESS_HISTORICAL_MESSAGES} historical messages per channel...")
        self.log(f"{'='*60}\n")

        # Get all configured channels
        # Block A V2.0 (A8): channel list now comes from Postgres
        # parser_sources via SchemaLoader.refresh_channels_from_db().
        # YAML ``channels:`` is fallback only.
        self.schema_loader.refresh_channels_from_db()
        all_channels = set(self.schema_loader.get_all_channels())

        # Limit to telegram channels (the historical loop is telegram-only;
        # OLX has its own crawler under telegram-ai/crawler-olx).
        # Filter is implicit: get_all_channels returns only entries with a
        # matching schema, and only telegram_channel rows from DB get one.

        self.log(f"Found {len(all_channels)} channels to process (from DB sources)")

        for username in all_channels:
            try:
                self.log(f"\nProcessing @{username}...")

                # Token-bucket acquire before each Telegram round-trip;
                # FloodWait on get_entity/get_messages shrinks this
                # channel's bucket so the next iteration of the loop
                # naturally slows down for it only.
                await self.rate_limiter.acquire(username)
                try:
                    channel = await self.client.get_entity(username)
                except FloodWaitError as fw:
                    self.log(
                        f"FloodWait on get_entity @{username}: {fw.seconds}s — backing off",
                        'WARNING',
                    )
                    self.rate_limiter.shrink_on_floodwait(username, fw.seconds)
                    await asyncio.sleep(fw.seconds)
                    continue
                except Exception as e:
                    self.log(f"Could not get channel @{username}: {e}", 'WARNING')
                    continue

                await self.rate_limiter.acquire(username)
                try:
                    messages = await self.client.get_messages(
                        channel,
                        limit=PROCESS_HISTORICAL_MESSAGES,
                    )
                except FloodWaitError as fw:
                    self.log(
                        f"FloodWait on get_messages @{username}: {fw.seconds}s — backing off",
                        'WARNING',
                    )
                    self.rate_limiter.shrink_on_floodwait(username, fw.seconds)
                    await asyncio.sleep(fw.seconds)
                    continue

                self.log(f"Retrieved {len(messages)} messages from @{username}")

                # Process each message
                for msg in messages:
                    self.stats['historical_processed'] += 1
                    self._bump_metric(username, parsed=1)

                    try:
                        success = await self.process_message(msg, is_historical=True)
                    except FloodWaitError as fw:
                        # FloodWait raised mid-message (e.g. on
                        # iter_messages for album expansion or
                        # download_media). Shrink this channel's
                        # bucket and skip the rest of this run.
                        self.log(
                            f"FloodWait in process_message @{username}: {fw.seconds}s",
                            'WARNING',
                        )
                        self.rate_limiter.shrink_on_floodwait(username, fw.seconds)
                        await asyncio.sleep(fw.seconds)
                        break

                    if success:
                        self.stats['historical_success'] += 1
                        self._bump_metric(username, saved=1)
                    else:
                        self.stats['historical_failed'] += 1
                        self._bump_metric(username, failed=1)

                    # Small delay to avoid rate limiting
                    await asyncio.sleep(1)

            except Exception as e:
                self.log(f"Error processing channel @{username}: {e}", 'ERROR')
                continue

        # Flush accumulated metrics to source_metric (A8)
        self.flush_metrics()

        self.log(f"\n{'='*60}")
        self.log(f"Historical Processing Complete!")
        self.log(f"{'='*60}")
        self.log(f"Total processed: {self.stats['historical_processed']}")
        self.log(f"Success: {self.stats['historical_success']}")
        self.log(f"Failed: {self.stats['historical_failed']}")
        self.log(f"{'='*60}\n")

    async def start(self):
        """Start the crawler"""
        self.log("Starting Flexible Crawler with Historical Processing...")
        self.log(f"Historical messages to process: {PROCESS_HISTORICAL_MESSAGES} per channel")

        await self.client.start(phone=phone_number)
        me = await self.client.get_me()
        self.log(f"Connected as: {me.first_name} (@{me.username})")

        # Process historical messages first
        await self.process_historical_messages()

        # Now set up real-time event handlers
        self.log("\n" + "="*60)
        self.log("Switching to REAL-TIME monitoring mode...")
        self.log("="*60 + "\n")

        @self.client.on(events.NewMessage())
        async def handle_new_message(event):
            """Handle new messages in real-time"""
            self.stats['realtime_processed'] += 1

            # Resolve channel up-front for the metric bump.
            channel_username = None
            try:
                if hasattr(event.message.peer_id, 'channel_id'):
                    ent = await self.client.get_entity(event.message.peer_id)
                    channel_username = getattr(ent, 'username', None)
            except Exception:
                pass
            if channel_username:
                self._bump_metric(channel_username, parsed=1)
                # Token-bucket: realtime messages also take a token so a
                # spammy channel hitting our flood-wait limit doesn't
                # stall the others.
                await self.rate_limiter.acquire(channel_username)

            try:
                success = await self.process_message(event.message, is_historical=False)
            except FloodWaitError as fw:
                self.log(
                    f"FloodWait realtime @{channel_username or '?'}: {fw.seconds}s",
                    'WARNING',
                )
                if channel_username:
                    self.rate_limiter.shrink_on_floodwait(channel_username, fw.seconds)
                # Don't blocking-sleep the event loop on realtime — the
                # next message for this channel will be naturally held
                # by the bucket's cooldown.
                success = False

            if success:
                self.stats['realtime_success'] += 1
                if channel_username:
                    self._bump_metric(channel_username, saved=1)
                self.log(f"\nReal-time Stats: Processed={self.stats['realtime_processed']}, "
                        f"Success={self.stats['realtime_success']}, "
                        f"Failed={self.stats['realtime_failed']}\n")
            else:
                self.stats['realtime_failed'] += 1
                if channel_username:
                    self._bump_metric(channel_username, failed=1)

            # Flush every 50 realtime messages so the admin dashboard
            # picks up movement without waiting for a restart.
            if self.stats['realtime_processed'] % 50 == 0:
                self.flush_metrics()

        # Block A V2.0 (A8) — periodic source-list refresh: pick up
        # admin-side pause/resume/add/delete every 5 minutes.
        async def _refresh_loop():
            while True:
                await asyncio.sleep(300)
                try:
                    self.schema_loader.refresh_channels_from_db()
                except Exception as e:
                    self.log(f"refresh_channels_from_db failed: {e}", "WARNING")

        asyncio.create_task(_refresh_loop())

        self.log("Now listening for new messages...")
        self.log("Press Ctrl+C to stop\n")

        # Keep running
        await self.client.run_until_disconnected()


async def main():
    """Main entry point"""
    crawler = FlexibleCrawler()
    await crawler.start()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[INFO] Crawler stopped by user")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
