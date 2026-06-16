# Admin Dashboard & Channel Management Guide

## 🎉 New Features Added

### ✅ Option A: Simple Admin Dashboard
**URL:** http://localhost:5000

A modern web dashboard with:
- **Real-time Statistics**: Total listings, channels, images, and today's activity
- **Listing Browser**: Search, filter, and view all crawled listings
- **Channel Activity Monitor**: See which channels are most active
- **Image Viewer**: View all images associated with listings
- **Auto-refresh**: Dashboard updates every 30 seconds

### ✅ Option C: Channel Configuration
**File:** `crawler/channels_config.yaml`

Control which channels to monitor with:
- **Whitelist Mode**: Only monitor specific channels
- **Blacklist Mode**: Monitor all channels except certain ones
- **Content Filters**: Require images, text, minimum length
- **Logging Options**: Verbose logging and log file support

---

## 📊 Using the Dashboard

### 1. Start the API Server
```bash
cd api
python server_sqlite.py
```

### 2. Open Dashboard
Navigate to: **http://localhost:5000**

You'll see:
- 📦 Total Listings
- 📺 Active Channels
- 🖼️ Total Images
- 📅 Today's Listings

### 3. Dashboard Features

**Search & Filter:**
- Search by description or channel name
- Filter by specific channel
- Sort by newest, oldest, or most images

**View Listing Details:**
- Click "View" button on any listing
- See full description
- View all associated images
- See metadata (ID, channel, date)

**Channel Statistics:**
- See listing count per channel
- Image count per channel
- Last activity timestamp

**Auto-refresh:**
- Dashboard automatically refreshes every 30 seconds
- Manual refresh with "🔄 Refresh" button

---

## ⚙️ Channel Configuration

### Configuration File
Location: `crawler/channels_config.yaml`

### Mode Options

**1. Whitelist Mode (Recommended)**
Only monitor specific channels:
```yaml
mode: whitelist

whitelist:
  - electronics_uz
  - smartphone_market
  - gadgets_tashkent
```

**2. Blacklist Mode**
Monitor all channels except specific ones:
```yaml
mode: blacklist

blacklist:
  - spam_channel
  - news_channel
```

**3. Monitor All**
No filtering, monitor every channel:
```yaml
mode: all
```

### Content Filters

**Require Images:**
```yaml
filters:
  require_images: true  # Skip messages without photos
```

**Require Text:**
```yaml
filters:
  require_text: true  # Skip messages without description
```

**Minimum Text Length:**
```yaml
filters:
  min_text_length: 10  # Skip messages with <10 characters
```

**Skip Forwarded Messages:**
```yaml
filters:
  skip_forwards: true  # Ignore forwarded content
```

**Skip Edited Messages:**
```yaml
filters:
  skip_edits: true  # Ignore edited messages
```

### Logging Configuration

**Enable Verbose Logging:**
```yaml
logging:
  verbose: true  # Print all processing events
```

**Log Skipped Messages:**
```yaml
logging:
  log_skipped: true  # Log why messages were skipped
```

**Save Logs to File:**
```yaml
logging:
  save_to_file: true
  log_file: crawler_log.txt
```

---

## 🚀 Complete Workflow

### Initial Setup

1. **Configure Telegram API** (`crawler/config.py`):
```python
api_id = 12345678  # From https://my.telegram.org
api_hash = 'your_hash_here'
phone_number = '+998991234567'
session_name = 'my_session'
```

2. **Configure Channels** (`crawler/channels_config.yaml`):
```yaml
mode: whitelist
whitelist:
  - your_channel_1
  - your_channel_2
```

3. **Install Dependencies**:
```bash
cd crawler
pip install -r requirements.txt
```

### Running the System

**Terminal 1 - Start API Server:**
```bash
cd api
python server_sqlite.py
```

**Terminal 2 - Start Crawler:**
```bash
cd crawler
python Crawler.py
```

**Browser - Open Dashboard:**
```
http://localhost:5000
```

### First-Time Crawler Setup
When you run `Crawler.py` for the first time:
1. Enter phone number (if not in config)
2. Enter verification code from Telegram
3. Enter 2FA password (if enabled)
4. Session is saved for future use

### Managing Channels

**Add New Channel to Whitelist:**
1. Edit `crawler/channels_config.yaml`
2. Add channel username to whitelist:
```yaml
whitelist:
  - existing_channel
  - new_channel  # Add this line
```
3. Restart crawler (Ctrl+C and restart)

**Remove Channel:**
1. Remove from whitelist in config
2. Restart crawler

**Monitor Without Filtering:**
```yaml
mode: all  # Monitor everything
```

---

## 📈 Monitoring & Statistics

### Dashboard Statistics (Real-time)

**Main Stats Card:**
- Total Listings: All listings ever crawled
- Channels: Number of unique channels
- Total Images: Total images uploaded
- Today's Listings: Listings created today

**Channel Activity:**
- Listings per channel
- Images per channel
- Last activity timestamp

### Log Files

**Location:** `crawler/crawler_log.txt`

**Log Format:**
```
[2025-10-15 14:30:00] INFO: Got album with 3 items from @electronics_uz
[2025-10-15 14:30:01] PROCESS: Processing album: iPhone 15 Pro Max...
[2025-10-15 14:30:02] SUCCESS: Created listing ID: 42
[2025-10-15 14:30:03] SUCCESS: Image uploaded successfully
[2025-10-15 14:30:10] SKIP: Skipping channel @spam_channel (not in whitelist)
```

**Log Levels:**
- `INFO`: General information
- `PROCESS`: Processing messages
- `SUCCESS`: Successful operations
- `SKIP`: Skipped messages/channels
- `ERROR`: Error conditions

---

## 🛠️ Troubleshooting

### Dashboard Not Loading

**Check API Server:**
```bash
curl http://localhost:5000/health
# Should return: {"status": "healthy", "database": "connected"}
```

**Check Port Conflict:**
```bash
# Windows
netstat -ano | findstr :5000

# Linux/Mac
lsof -ti:5000
```

### Crawler Not Processing Channels

**Check Configuration:**
```bash
cat crawler/channels_config.yaml
```

**Verify Channel Names:**
- Use channel username WITHOUT @ symbol
- Example: `electronics_uz` not `@electronics_uz`

**Check Logs:**
```bash
tail -f crawler/crawler_log.txt
```

### No Listings Appearing

**Common Issues:**
1. Channel not in whitelist
2. Messages don't meet filter criteria
3. Messages don't have required images/text
4. Crawler not running

**Debug Steps:**
```bash
# Check if crawler is running
ps aux | grep Crawler.py

# Check filter settings
cat crawler/channels_config.yaml | grep filters -A 10

# Temporarily disable filters
# Set all filters to false for testing
```

---

## 📝 Configuration Examples

### Example 1: Electronics Marketplace
```yaml
mode: whitelist
whitelist:
  - electronics_uz
  - smartphone_market
  - gadgets_tashkent
  - tech_deals_uz

filters:
  require_images: true
  require_text: true
  min_text_length: 20
  skip_forwards: false
  skip_edits: true

logging:
  verbose: true
  log_skipped: true
  save_to_file: true
  log_file: electronics_crawler.log
```

### Example 2: General Monitoring (Development)
```yaml
mode: all

filters:
  require_images: false  # Allow messages without images
  require_text: false    # Allow messages without text
  min_text_length: 0
  skip_forwards: false
  skip_edits: false

logging:
  verbose: true
  log_skipped: false  # Don't log skipped messages
  save_to_file: false
```

### Example 3: Strict Filtering
```yaml
mode: whitelist
whitelist:
  - verified_channel_1
  - verified_channel_2

filters:
  require_images: true
  require_text: true
  min_text_length: 50  # Require detailed descriptions
  skip_forwards: true   # Only original content
  skip_edits: true      # No edited messages

logging:
  verbose: false  # Quiet mode
  log_skipped: false
  save_to_file: true
  log_file: strict_crawler.log
```

---

## 🔐 Security Notes

- ✅ Dashboard runs on localhost only (not exposed to internet)
- ✅ No authentication required for local development
- ✅ Telegram credentials stored in config.py (git-ignored)
- ⚠️ For production: Add authentication, HTTPS, rate limiting

---

## 📚 API Endpoints

All endpoints available at `http://localhost:5000`

**Dashboard:**
- `GET /` - Admin dashboard UI

**Statistics:**
- `GET /api/Crawler/statistics` - System statistics
- `GET /api/Crawler/channel-stats` - Per-channel statistics

**Listings:**
- `GET /api/Crawler/listings` - List all listings (paginated)
- `GET /api/Crawler/listings/{id}` - Get listing details with images
- `POST /api/Crawler` - Create new listing (used by crawler)
- `POST /api/Crawler/listing/images` - Upload images (used by crawler)

**Utility:**
- `GET /health` - Health check
- `GET /uploads/{filename}` - Serve uploaded images

---

## 🎯 Next Steps

1. **Configure** your Telegram API credentials
2. **Add channels** to the whitelist in channels_config.yaml
3. **Start** the API server
4. **Run** the crawler
5. **Open** the dashboard at http://localhost:5000
6. **Subscribe** your Telegram account to marketplace channels
7. **Monitor** listings flowing in!

For detailed setup instructions, see: [SETUP.md](SETUP.md)
