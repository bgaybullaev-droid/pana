# Telegram AI - Complete Setup Guide

## 📋 Project Overview

**Telegram AI** is a bot system that automatically crawls product listings from Telegram channels and stores them in a centralized database via a REST API.

### Business Process Flow
1. **Telegram Bot listens** to subscribed channels
2. **New messages arrive** (product listings with images and text)
3. **Bot extracts** text description, username, message ID
4. **Posts to API** → receives listing ID
5. **Uploads images** associated with that listing
6. **Cleans up** temporary files

### Architecture Components
- **Crawler Bot** (`crawler/Crawler.py`): Telethon-based Telegram client
- **REST API** (`api/server_sqlite.py`): Flask server with SQLite database
- **Database**: SQLite for development (PostgreSQL available via Docker)
- **File Storage**: Local uploads directory

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Python 3.8+ installed
- Docker installed (optional, for PostgreSQL)
- Git (for cloning)

### Step 1: Install Dependencies
```bash
# Install crawler dependencies
cd crawler
pip install -r requirements.txt

# Install API dependencies
cd ../api
pip install -r requirements.txt
```

### Step 2: Start the API Server
```bash
cd api
python server_sqlite.py
```

The API will start on `http://localhost:5000`

### Step 3: Test the System
Open a new terminal:
```bash
python test_system.py
```

You should see:
```
🎉 ALL TESTS PASSED! System is working correctly!
```

---

## 🔧 Full System Setup

### API Server Setup

#### Option A: SQLite (Recommended for Development)
```bash
cd api
python server_sqlite.py
```

**Advantages:**
- No setup required
- Lightweight
- Fast for development
- Auto-creates database on first run

#### Option B: PostgreSQL with Docker
```bash
# Start PostgreSQL
docker-compose up -d

# Verify it's running
docker ps | grep telegram-ai-db

# Start API server (PostgreSQL version)
cd api
python server.py
```

**Advantages:**
- Production-ready
- Better performance at scale
- Relational integrity

**Access pgAdmin**: http://localhost:5050
- Email: admin@telegram-ai.local
- Password: admin123

### Telegram Bot Setup

#### 1. Get Telegram API Credentials
1. Visit https://my.telegram.org
2. Log in with your phone number
3. Go to "API Development Tools"
4. Create a new application
5. Copy `api_id` and `api_hash`

#### 2. Configure the Bot
Edit `crawler/config.py`:
```python
api_id = YOUR_API_ID_HERE  # Integer, e.g., 12345678
api_hash = 'YOUR_API_HASH_HERE'  # String, e.g., '1a2b3c4d5e6f...'
phone_number = '+998XXXXXXXXX'  # Your phone number
session_name = 'my_bot_session'
```

#### 3. Run the Bot
```bash
cd crawler
python Crawler.py
```

**First run**: You'll be prompted to enter:
1. Your phone number (if not in config.py)
2. Verification code sent to Telegram
3. (Optional) 2FA password if enabled

**Subsequent runs**: The session is saved, no re-authentication needed.

---

## 📊 API Endpoints

### Base URL
```
http://localhost:5000
```

### Available Endpoints

#### 1. Health Check
```http
GET /health
```

**Response:**
```json
{
    "status": "healthy",
    "database": "connected"
}
```

#### 2. Create Listing
```http
POST /api/Crawler
Content-Type: application/json

{
    "description": "Product description here",
    "userName": "channel_username",
    "messageId": 12345
}
```

**Response:**
```json
{
    "id": 1,
    "description": "Product description here",
    "user_name": "channel_username",
    "message_id": 12345,
    "created_at": "2024-10-15 12:00:00"
}
```

#### 3. Upload Images
```http
POST /api/Crawler/listing/images
Content-Type: multipart/form-data

listingId=1
ListingImages=<file>
```

**Response:**
```json
{
    "success": true,
    "message": "Image uploaded successfully",
    "image_id": 1,
    "filename": "listing_1_20241015_120000_product.jpg"
}
```

#### 4. Get All Listings
```http
GET /api/Crawler/listings?page=1&per_page=10
```

**Response:**
```json
{
    "total": 50,
    "page": 1,
    "per_page": 10,
    "listings": [...]
}
```

#### 5. Get Listing Details
```http
GET /api/Crawler/listings/{id}
```

**Response:**
```json
{
    "id": 1,
    "description": "...",
    "user_name": "...",
    "images": [
        {
            "id": 1,
            "image_path": "uploads/...",
            "original_filename": "product.jpg",
            "file_size": 123456
        }
    ]
}
```

---

## 🧪 Testing

### Run Comprehensive Tests
```bash
python test_system.py
```

This tests:
1. ✅ API Health Check
2. ✅ Create Listing
3. ✅ Upload Image
4. ✅ Get All Listings
5. ✅ Get Listing Details
6. ✅ Complete Workflow Simulation

### Manual API Testing with curl

**Create a listing:**
```bash
curl -X POST http://localhost:5000/api/Crawler \
  -H "Content-Type: application/json" \
  -d '{"description":"Test Product","userName":"test_user","messageId":99999}'
```

**Upload an image:**
```bash
curl -X POST http://localhost:5000/api/Crawler/listing/images \
  -F "listingId=1" \
  -F "ListingImages=@/path/to/image.jpg"
```

**Get listings:**
```bash
curl http://localhost:5000/api/Crawler/listings
```

---

## 🗂️ Project Structure

```
telegram-ai/
├── api/
│   ├── server.py                 # PostgreSQL version
│   ├── server_sqlite.py          # SQLite version (recommended)
│   ├── requirements.txt          # API dependencies
│   └── init.sql                  # PostgreSQL initialization
├── crawler/
│   ├── Crawler.py                # Main bot (production)
│   ├── config.py                 # Telegram credentials
│   ├── requirements.txt          # Bot dependencies
│   ├── test.py                   # Basic Telegram examples
│   └── test02.py                 # Event handling with NLP
├── extractor/
│   ├── test.py                   # BERT multilingual experiment
│   └── requirements.txt          # ML dependencies
├── uploads/                      # Uploaded images storage
├── docker-compose.yml            # PostgreSQL + pgAdmin setup
├── test_system.py                # Comprehensive system tests
├── SETUP.md                      # This file
├── CLAUDE.md                     # Claude Code guidance
└── README.md                     # Project overview
```

---

## 🔍 Troubleshooting

### API Server Issues

**Port 5000 already in use:**
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:5000 | xargs kill -9
```

**Database locked (SQLite):**
```bash
# Stop all API server instances
# Delete telegram_listings.db
# Restart server (will recreate database)
```

### Telegram Bot Issues

**Authentication failed:**
- Delete session file (`*.session`)
- Run bot again and re-authenticate

**"Photo not found" error:**
- Check message actually has images
- Verify bot has access to the channel
- Check message isn't too old (>48 hours)

**"Connection timeout":**
- Check internet connection
- Verify Telegram isn't blocked
- Try different session name

### Docker Issues

**PostgreSQL won't start:**
```bash
# Check logs
docker logs telegram-ai-db

# Restart container
docker restart telegram-ai-db

# Full reset
docker-compose down -v
docker-compose up -d
```

---

## 🎯 Next Steps

### For Development
1. Add error handling and logging
2. Implement retry logic for failed uploads
3. Add database backup mechanism
4. Create admin dashboard for listings

### For Production
1. Switch to PostgreSQL
2. Add authentication/authorization
3. Implement rate limiting
4. Set up monitoring and alerts
5. Configure HTTPS/SSL
6. Deploy to cloud (AWS/Azure/GCP)

---

## 📞 Support

For issues or questions:
1. Check this documentation
2. Review error logs in terminal
3. Test with `python test_system.py`
4. Check GitHub issues (if applicable)

---

## 📝 License

[Your License Here]

---

**Last Updated:** October 15, 2025
**Version:** 1.0.0 (Revived)
