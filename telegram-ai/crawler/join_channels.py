#!/usr/bin/env python3
"""
Automatically join all channels configured in schema files.
Run this once to join all channels before starting the crawler.
"""

import asyncio
import yaml
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import FloodWaitError, ChannelPrivateError, UsernameInvalidError
import time

# Import config
try:
    from config import api_id, api_hash, phone_number, session_name
except ImportError:
    print("[ERROR] config.py not found!")
    print("Please create crawler/config.py with your Telegram credentials.")
    print("\nExample:")
    print("api_id = 12345678")
    print("api_hash = 'your_api_hash_here'")
    print("phone_number = '+998901234567'")
    print("session_name = 'main_session'")
    exit(1)


def load_channels_from_schemas():
    """Load all channel usernames from YAML schema files"""
    channels = []
    schema_dir = Path(__file__).parent / 'schemas'

    if not schema_dir.exists():
        print(f"[WARNING] Schema directory not found: {schema_dir}")
        return channels

    print(f"\n[INFO] Loading schemas from: {schema_dir}")

    for schema_file in schema_dir.glob('*.yaml'):
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema = yaml.safe_load(f)
                schema_channels = schema.get('channels', [])
                if schema_channels:
                    print(f"  - {schema_file.name}: {len(schema_channels)} channels")
                    channels.extend(schema_channels)
        except Exception as e:
            print(f"[WARNING] Could not load {schema_file.name}: {e}")

    # Remove duplicates while preserving order
    unique_channels = []
    seen = set()
    for ch in channels:
        if ch not in seen:
            unique_channels.append(ch)
            seen.add(ch)

    return unique_channels


async def join_channel(client, username):
    """Join a single channel"""
    try:
        # Try to get the channel entity
        entity = await client.get_entity(username)

        # Check if already joined
        try:
            participant = await client.get_permissions(entity)
            if participant:
                print(f"  [SKIP] Already joined: @{username}")
                return True
        except:
            pass

        # Join the channel
        await client(JoinChannelRequest(entity))
        print(f"  [OK] Joined: @{username}")
        return True

    except ChannelPrivateError:
        print(f"  [ERROR] Private channel (need invite): @{username}")
        return False
    except UsernameInvalidError:
        print(f"  [ERROR] Invalid username: @{username}")
        return False
    except FloodWaitError as e:
        print(f"  [WAIT] Rate limited. Waiting {e.seconds} seconds...")
        await asyncio.sleep(e.seconds)
        return await join_channel(client, username)  # Retry
    except Exception as e:
        print(f"  [ERROR] Could not join @{username}: {e}")
        return False


async def main():
    """Main function"""
    print("="*60)
    print("Telegram Channel Auto-Join Script")
    print("="*60)

    # Load channels
    channels = load_channels_from_schemas()

    if not channels:
        print("\n[ERROR] No channels found in schema files!")
        print("Please add channels to crawler/schemas/*.yaml files")
        return

    print(f"\n[INFO] Found {len(channels)} channels to join:\n")
    for i, ch in enumerate(channels, 1):
        print(f"  {i:2d}. @{ch}")

    print(f"\n[INFO] Connecting to Telegram...")

    # Create client
    client = TelegramClient(session_name, api_id, api_hash)

    try:
        await client.start(phone=phone_number)
        print(f"[OK] Connected as: {(await client.get_me()).first_name}")

        # Import JoinChannelRequest here (after client is connected)
        from telethon.tl.functions.channels import JoinChannelRequest

        print(f"\n[INFO] Joining channels...\n")

        success_count = 0
        failed_count = 0

        for i, username in enumerate(channels, 1):
            print(f"[{i}/{len(channels)}] Joining @{username}...")

            result = await join_channel(client, username)

            if result:
                success_count += 1
            else:
                failed_count += 1

            # Rate limiting: wait 2 seconds between joins
            if i < len(channels):
                await asyncio.sleep(2)

        print("\n" + "="*60)
        print("Summary:")
        print("="*60)
        print(f"Total channels: {len(channels)}")
        print(f"Successfully joined: {success_count}")
        print(f"Failed: {failed_count}")
        print("="*60)

        if success_count > 0:
            print("\n[OK] You can now start the crawler!")
            print("Run: python FlexibleCrawler.py")

    except Exception as e:
        print(f"\n[ERROR] {e}")
    finally:
        await client.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
