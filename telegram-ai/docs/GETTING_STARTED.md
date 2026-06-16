# Getting Started - Telegram AI Crawler

## 🚀 Quick Start (5 Minutes)

### Step 1: Navigate to Crawler Directory

```bash
cd crawler
```

### Step 2: Run Setup

**Windows:**
```bash
setup.bat
```

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

### Step 3: Configure API Keys

Edit `crawler/.env`:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-your-key-here
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_hash_here
TELEGRAM_PHONE_NUMBER=+998901234567
```

**Get keys:**
- Anthropic: https://console.anthropic.com/
- Telegram: https://my.telegram.org/apps

### Step 4: Add Your Channels

Edit `crawler/schemas/product_listing.yaml`:

```yaml
channels:
  - your_channel_username
  - electronics_uz
```

### Step 5: Run!

**Terminal 1 - API Server:**
```bash
cd api
python server_llm.py
```

**Terminal 2 - Crawler:**
```bash
cd crawler
python FlexibleCrawler.py
```

## 📁 Project Structure

```
telegram-ai/
├── crawler/                      # ← All crawler code here
│   ├── .env                      # ← Your API keys (edit this!)
│   ├── .env.example             # ← Template
│   ├── setup.bat / setup.sh     # ← Setup scripts
│   ├── llm_config.py            # ← Configuration
│   ├── llm_extractor.py         # ← LLM-based extraction
│   ├── image_embeddings.py      # ← CLIP embeddings
│   ├── vector_db.py             # ← Vector database
│   ├── FlexibleCrawler.py       # ← Main crawler
│   ├── schemas/                 # ← Channel schemas
│   │   ├── product_listing.yaml
│   │   ├── job_posting.yaml
│   │   └── real_estate.yaml
│   └── requirements.txt         # ← Dependencies
│
├── api/                         # API server
│   └── server_llm.py
│
└── docs/                        # Documentation
    ├── LLM_CRAWLER_GUIDE.md
    ├── ENV_SETUP_GUIDE.md
    └── QUICK_START_LLM.md
```

## 📖 Documentation

- **`crawler/README.md`** - Crawler quick start
- **`ENV_SETUP_GUIDE.md`** - Environment setup
- **`LLM_CRAWLER_GUIDE.md`** - Complete guide (720 lines)
- **`LLM_IMPLEMENTATION_SUMMARY.md`** - Technical details
- **`FLEXIBLE_SCHEMA_GUIDE.md`** - Schema creation

## 💡 What This Does

### LLM-Based Extraction
Handles **any posting format** - no regex patterns needed!

```
Input (different formats):
"3-xonali, 120k$, Chilonzor"
"3 rooms apt, $120k, Chilanzor"
"Квартира 3-комнатная, 120.000$"

Output (all → same structure):
{
  "rooms": 3,
  "price": 120000,
  "district": "Chilonzor"
}
```

### Image Similarity (Like Instagram)
Uses CLIP to detect duplicate images across channels:

```
Channel A: [Photo of apartment]
Channel B: [Same apartment, different angle]
→ Detected! Similarity: 0.89
→ Flagged as duplicate
```

### Cost-Effective
- **LLM:** ~$3 per 1000 messages
- **Image embeddings:** FREE (CLIP runs locally)
- **Vector search:** FREE (ChromaDB)

## 🎯 Use Cases

1. **Real Estate Aggregator**
   - Crawl 50+ property channels
   - Detect same apartments in different channels
   - Build searchable database

2. **E-Commerce Price Tracker**
   - Monitor product listings
   - Track price changes
   - Alert on deals

3. **Job Board**
   - Aggregate job postings
   - Remove duplicates
   - Categorize by industry

## 🔧 Helper Scripts

After setup, you'll have:

**Windows:**
- `start_crawler.bat` - Start crawler
- `start_api.bat` - Start API server
- `test_llm.bat` - Test configuration
- `test_clip.bat` - Test image embeddings

**Linux/Mac:**
- `./start_crawler.sh` - Start crawler
- `./start_api.sh` - Start API server
- `./test_llm.sh` - Test configuration
- `./test_clip.sh` - Test image embeddings

## 🛠️ Configuration

All configuration is in `crawler/.env`:

```bash
# LLM Settings
ANTHROPIC_API_KEY=your-key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Telegram
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_hash

# Image Processing
CLIP_DEVICE=cuda  # or 'cpu'
IMAGE_SIMILARITY_THRESHOLD=0.88

# Duplicate Handling
DUPLICATE_ACTION=skip  # or 'flag', 'merge'
```

## 📊 Monitoring

**Check if it's working:**
```bash
# Health check
curl http://localhost:5000/health

# Statistics
curl http://localhost:5000/api/Crawler/statistics

# View duplicates
curl http://localhost:5000/api/Crawler/duplicates
```

## ⚠️ Troubleshooting

**"Could not load .env file"**
```bash
cd crawler
pip install python-dotenv
```

**"API key not set"**
- Edit `crawler/.env`
- Add your `ANTHROPIC_API_KEY`

**"No messages being processed"**
- Channels must be in schema YAML files
- Bot must be subscribed to channels

**"CUDA not available"**
- Normal if no GPU
- CLIP will use CPU (slower but works)

## 🔒 Security

**Protected files** (in `.gitignore`):
- `crawler/.env` - API keys
- `*.session` - Telegram auth
- `*.db` - Your data

**Safe to share:**
- `crawler/.env.example` - Template
- All code files
- Documentation

## 📞 Support

**Test your setup:**
```bash
cd crawler
python llm_config.py
```

Should show:
```
✓ Loaded environment variables
✅ Configuration valid!
LLM Provider: anthropic
```

## 🎉 Ready!

1. ✅ Run `cd crawler && setup.bat`
2. ✅ Edit `crawler/.env` with your keys
3. ✅ Add channels to schemas
4. ✅ Start crawling!

---

**Built with Claude Code** | LLM + Vector DB | Instagram-quality duplicate detection

**Status:** Production Ready ✅
