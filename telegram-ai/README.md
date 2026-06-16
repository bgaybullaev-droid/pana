# Telegram AI - Product Listing Crawler Bot

**Status:** ✅ Fully Operational (Revived October 2025)

## Overview

Telegram AI is an automated bot system that crawls product listings from Telegram channels and centralizes them in a database via a REST API. Perfect for aggregating marketplace data, tracking product announcements, and building e-commerce analytics.

### Features
- 🤖 Automated Telegram channel monitoring
- 📸 Image extraction and storage
- 🗄️ SQLite or PostgreSQL database support
- 🚀 REST API for data access
- 📊 **Admin Dashboard** with real-time statistics (NEW!)
- ⚙️ **Channel filtering** with whitelist/blacklist (NEW!)
- 🧪 Comprehensive test suite
- 📈 Activity monitoring and logging

## Quick Start (3 Steps)

### 1. Install Dependencies
```bash
# API Server
cd api
pip install -r requirements.txt

# Telegram Bot
cd ../crawler
pip install -r requirements.txt
```

### 2. Start the System
```bash
# Windows
start_system.bat

# Linux/Mac
bash start_system.sh
```

### 3. Test Everything Works
```bash
python test_system.py
```

You should see: **🎉 ALL TESTS PASSED!**

## Architecture

```
Telegram Channel → Bot (Telethon) → REST API (Flask) → Database (SQLite/PostgreSQL)
                                           ↓
                                    Image Storage (uploads/)
```

### Components
- **Crawler** (`crawler/Crawler.py`): Listens to Telegram channels, extracts listings
- **API Server** (`api/server_sqlite.py`): Flask REST API with SQLite
- **Admin Dashboard** (http://localhost:5000): Web UI for monitoring
- **Channel Config** (`crawler/channels_config.yaml`): Filter settings
- **Database**: Stores listings and image metadata
- **Test Suite** (`test_system.py`): Validates entire system

## Business Process

1. Bot subscribes to Telegram marketplace channels
2. New product listing arrives (text + images)
3. Bot extracts:
   - Product description
   - Channel username
   - Message ID
   - Associated images
4. Posts text to API → receives listing ID
5. Uploads images linked to listing ID
6. Data accessible via REST API

## API Endpoints

**Base URL:** `http://localhost:5000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/Crawler` | Create listing |
| POST | `/api/Crawler/listing/images` | Upload images |
| GET | `/api/Crawler/listings` | Get all listings |
| GET | `/api/Crawler/listings/{id}` | Get listing details |

## Configuration

### Telegram Bot Setup
Edit `crawler/config.py`:
```python
api_id = 12345678  # From https://my.telegram.org
api_hash = 'your_hash_here'
phone_number = '+998XXXXXXXXX'
session_name = 'my_bot_session'
```

### Database Options

**Option A: SQLite (Default - No Setup Required)**
```bash
cd api
python server_sqlite.py
```

**Option B: PostgreSQL with Docker**
```bash
docker-compose up -d
cd api
python server.py
```

## Testing

### Automated Tests
```bash
python test_system.py
```

Tests:
- ✅ API health check
- ✅ Create listing
- ✅ Upload images
- ✅ Retrieve data
- ✅ End-to-end workflow

### Manual Testing
```bash
# Health check
curl http://localhost:5000/health

# Create listing
curl -X POST http://localhost:5000/api/Crawler \
  -H "Content-Type: application/json" \
  -d '{"description":"Test","userName":"test","messageId":123}'

# Get listings
curl http://localhost:5000/api/Crawler/listings
```

## Project Structure

```
telegram-ai/
├── api/
│   ├── server_sqlite.py       # SQLite API server (recommended)
│   ├── server.py              # PostgreSQL API server
│   └── requirements.txt
├── crawler/
│   ├── Crawler.py             # Main bot (production)
│   ├── config.py              # Credentials configuration
│   └── requirements.txt
├── extractor/
│   └── test.py                # NLP experiments (optional)
├── uploads/                   # Uploaded images
├── test_system.py             # Comprehensive tests
├── start_system.bat           # Windows startup
├── start_system.sh            # Linux/Mac startup
├── SETUP.md                   # Detailed setup guide
└── CLAUDE.md                  # Claude Code guidance
```

## Documentation

- **[SETUP.md](SETUP.md)** - Complete setup and configuration guide
- **[DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md)** - Dashboard & channel management guide
- **[CLAUDE.md](CLAUDE.md)** - Architectural documentation for developers

## Troubleshooting

**API won't start (port conflict):**
```bash
# Windows: netstat -ano | findstr :5000
# Linux/Mac: lsof -ti:5000 | xargs kill -9
```

**Bot authentication fails:**
- Delete `*.session` file
- Run bot again and re-authenticate

**Database locked:**
- Stop all API instances
- Delete `telegram_listings.db`
- Restart (will recreate)

See [SETUP.md](SETUP.md) for more troubleshooting.

## Development

### Adding Features
1. API endpoints: Edit `api/server_sqlite.py`
2. Bot logic: Edit `crawler/Crawler.py`
3. Tests: Update `test_system.py`

### Database Schema

**listings** table:
- id (PRIMARY KEY)
- description (TEXT)
- user_name (VARCHAR)
- message_id (INTEGER)
- channel_username (VARCHAR)
- created_at (TIMESTAMP)

**listing_images** table:
- id (PRIMARY KEY)
- listing_id (FOREIGN KEY)
- image_path (VARCHAR)
- original_filename (VARCHAR)
- file_size (INTEGER)
- created_at (TIMESTAMP)

## Admin Dashboard

**Access:** http://localhost:5000 (after starting API server)

**Features:**
- 📊 Real-time statistics (listings, channels, images)
- 🔍 Search and filter listings
- 📺 Channel activity monitoring
- 🖼️ Image viewer with modal popups
- 🔄 Auto-refresh every 30 seconds

**See:** [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) for complete guide

## Channel Management

**Configuration File:** `crawler/channels_config.yaml`

**Modes:**
- **Whitelist**: Only monitor specific channels
- **Blacklist**: Monitor all except specific channels
- **All**: Monitor every channel

**Content Filters:**
- Require images/text
- Minimum text length
- Skip forwards/edits

**See:** [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) for examples

## Next Steps

- [ ] Add Telegram credentials to `crawler/config.py`
- [ ] Configure channels in `crawler/channels_config.yaml`
- [ ] Subscribe bot to marketplace channels
- [ ] Open dashboard at http://localhost:5000
- [ ] Run production bot: `cd crawler && python Crawler.py`
- [ ] Deploy to production server

## License

[Your License Here]

## Credits

**Original Development:** 2022-2023
**Revival & Modernization:** October 2025
**Stack:** Python, Telethon, Flask, SQLite/PostgreSQL, Docker

---

**Status:** Production Ready ✅
**Last Updated:** October 15, 2025
**Python Version:** 3.8+
