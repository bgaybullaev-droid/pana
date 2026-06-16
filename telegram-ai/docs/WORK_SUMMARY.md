# Work Summary: Telegram Crawler LLM Integration

## Overview

This document summarizes the work completed on the Telegram Crawler project, specifically the LLM provider integration for extracting structured data from Telegram channel messages.

---

## Final Configuration

The system is configured to use **OpenAI GPT-4o-mini** for LLM-based text extraction.

### Current `.env` Settings
```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxx
OPENAI_MODEL=gpt-4o-mini
```

### Supported LLM Providers
- **OpenAI** (active) - `gpt-4o-mini`
- **Anthropic** (available) - `claude-3-5-sonnet-20241022`

---

## Work Completed

### 1. Web Scraper Implementation
Created `telegram_web_scraper.py` - a web-based scraper for public Telegram channels that:
- Fetches posts from `https://t.me/s/{channel}` without authentication
- Parses HTML to extract message text, images, and metadata
- No Telegram API credentials required for public channels

### 2. LLM Extractor (`llm_extractor.py`)
Implemented schema-aware LLM extraction system:
- Supports OpenAI and Anthropic providers
- Uses structured prompts for consistent JSON output
- Handles multiple languages (Uzbek, Russian, English)
- Includes retry logic and error handling

### 3. LLM Configuration (`llm_config.py`)
Centralized configuration file with:
- Provider selection via environment variables
- Model configuration
- Temperature, token limits, and retry settings
- Response caching options

### 4. Crawler Service (`api/crawler_service.py`)
Backend service that orchestrates:
- Web scraping from Telegram channels
- LLM-based data extraction
- CSV export functionality

### 5. CSV Exporter (`csv_exporter.py`)
Utility for exporting extracted data:
- Handles CSV file operations
- Saves images to output directory
- Thread-safe for concurrent operations

### 6. Dashboard UI
Web dashboard for monitoring and control:
- Real-time listings view
- CSV export tab with crawl controls
- Channel selection and crawl progress tracking

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Telegram Channels                         │
│                  (Public web interface)                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              telegram_web_scraper.py                         │
│         Scrapes t.me/s/{channel} HTML pages                  │
│              (No authentication required)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  llm_extractor.py                            │
│         Extracts structured data using OpenAI GPT            │
│                                                              │
│    ┌─────────────────────────────────────────────────┐      │
│    │  Supported Providers:                            │      │
│    │  • OpenAI (gpt-4o-mini) ← ACTIVE                │      │
│    │  • Anthropic (claude-3-5-sonnet)                │      │
│    └─────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  csv_exporter.py                             │
│                    CSV Export                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Files

| File | Purpose |
|------|---------|
| `crawler/.env` | Environment variables (API keys, provider selection) |
| `crawler/llm_config.py` | LLM configuration and settings |
| `crawler/llm_extractor.py` | LLM-based data extraction logic |
| `crawler/telegram_web_scraper.py` | Web scraper for public Telegram channels |
| `crawler/csv_exporter.py` | CSV export utility |
| `api/crawler_service.py` | Backend crawler service |
| `api/server_sqlite.py` | Flask API server |
| `api/static/dashboard.js` | Dashboard frontend |

---

## How to Run

### Start the API Server
```bash
cd /mnt/projects/data/siddiq/telegram-ai/api
python server_sqlite.py
```

### Access the Dashboard
Open `http://localhost:5002` in your browser.

### Run a Crawl
1. Go to the "CSV Export" tab
2. Select channels to crawl
3. Set messages per channel
4. Click "Start Crawl"

---

## Cost Estimate

Using OpenAI `gpt-4o-mini`:
- ~$0.00015 per 1K input tokens
- ~$0.0006 per 1K output tokens
- Estimated: ~$0.50-1.00 per 1000 messages

---

## Future Considerations

1. **Anthropic Claude**: Available as alternative, just change:
   ```
   LLM_PROVIDER=anthropic
   ANTHROPIC_API_KEY=your-key
   ```

2. **Local LLM (Ollama)**: Could be added if running on the same server as the crawler.
