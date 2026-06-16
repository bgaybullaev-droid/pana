# Telegram AI Crawler - Quick Start

## 🚀 One-Command Setup

### Windows
```bash
setup.bat
```

### Linux/Mac
```bash
chmod +x setup.sh
./setup.sh
```

This will:
- ✅ Create virtual environment
- ✅ Install all dependencies (PyTorch, CLIP, ChromaDB, etc.)
- ✅ Test installation
- ✅ Create helper scripts

## ⚙️ Configuration

### 1. Edit `.env` File

Open `.env` in this directory and add your API keys:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-your-key-here
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_hash_here
TELEGRAM_PHONE_NUMBER=+998901234567
```

**Get API keys:**
- Anthropic: https://console.anthropic.com/
- Telegram: https://my.telegram.org/apps

### 2. Add Your Channels

Edit `schemas/product_listing.yaml`:

```yaml
channels:
  - your_channel_username
  - electronics_uz
```

### 3. Test Configuration

```bash
python llm_config.py
```

You should see:
```
✓ Loaded environment variables
✅ Configuration valid!
```

## ▶️ Run the Crawler

### Start API Server (Terminal 1)
```bash
cd ..
python api/server_llm.py
```

### Start Crawler (Terminal 2)
```bash
python FlexibleCrawler.py
```

Or use the helper scripts created by setup:
- **Windows:** `start_crawler.bat`
- **Linux/Mac:** `./start_crawler.sh`

## 📊 What It Does

1. **Monitors Telegram channels** you specify in schemas
2. **Extracts data with LLM** (Claude/GPT) - handles any format!
3. **Generates image embeddings** with CLIP (free, local)
4. **Detects duplicates** using vector similarity (like Instagram)
5. **Stores in database** with SQLite

## 💰 Cost

- **LLM extraction:** ~$3 per 1000 messages
- **Image embeddings:** FREE (CLIP runs locally)
- **Vector search:** FREE (ChromaDB)
- **Total:** ~$3-5 per 1000 messages

## 📖 Full Documentation

- `ENV_SETUP_GUIDE.md` - Environment setup
- `../LLM_CRAWLER_GUIDE.md` - Complete guide
- `../LLM_IMPLEMENTATION_SUMMARY.md` - Technical details
- `../FLEXIBLE_SCHEMA_GUIDE.md` - Schema creation

## 🛠️ Files in This Directory

```
crawler/
├── .env                    # Your API keys (edit this!)
├── .env.example           # Template
├── setup.bat / setup.sh   # Setup scripts
├── llm_config.py          # Configuration loader
├── llm_extractor.py       # LLM-based extraction
├── image_embeddings.py    # CLIP embeddings
├── vector_db.py           # ChromaDB similarity search
├── FlexibleCrawler.py     # Main crawler
├── config.py              # Telegram credentials
├── schemas/               # Channel schemas
│   ├── product_listing.yaml
│   ├── job_posting.yaml
│   └── real_estate.yaml
└── requirements.txt       # Dependencies
```

## 🔧 Troubleshooting

**"Could not load .env file"**
- Run: `pip install python-dotenv`

**"API key not set"**
- Edit `.env` and add your `ANTHROPIC_API_KEY`

**"CUDA not available"**
- Normal if no GPU. CLIP will use CPU (slower but works)

**"No messages being processed"**
- Check channels are in schema YAML files
- Bot must be subscribed to channels

## 📝 Next Steps

1. ✅ Run `setup.bat` or `setup.sh`
2. ✅ Edit `.env` with your API keys
3. ✅ Add channels to schemas
4. ✅ Test with `python llm_config.py`
5. ✅ Start the system!

---

**Built with LLM + Vector DB** | Cost-effective | Instagram-quality duplicate detection
