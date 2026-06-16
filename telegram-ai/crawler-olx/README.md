# OLX.uz Real Estate Crawler

Automated crawler for OLX.uz real estate listings. Converts HTML → Markdown → JSON using Playwright and LLM extraction (OpenAI or Google Gemini).

## How It Works

```
┌────────────────────────────────────────────────────────────────────┐
│  STEP 1: Go to category page                                       │
│  https://www.olx.uz/nedvizhimost/                                  │
│                                                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ Listing  │ │ Listing  │ │ Listing  │ │ Listing  │  ... (many)  │
│  │  Card 1  │ │  Card 2  │ │  Card 3  │ │  Card 4  │              │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│  STEP 2: Collect all listing URLs                                  │
│                                                                    │
│  - /d/obyavlenie/3-honali-kvartira-sotiladi-ID4hiGs.html          │
│  - /d/obyavlenie/kvartira-mirobod-tuman-ID4hj2K.html              │
│  - ... (30-40 URLs per page)                                       │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│  STEP 3: Enter EACH listing URL                                    │
│                                                                    │
│  For each URL:                                                     │
│    1. page.goto(listing_url)                                       │
│    2. html = page.content()                                        │
│    3. markdown = html_to_markdown(html)                            │
│    4. json_data = llm_extractor.extract(markdown)                  │
│    5. Push to backend API + save to output/                        │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│  STEP 4: Go to next page, repeat                                   │
│                                                                    │
│  https://www.olx.uz/nedvizhimost/?page=2                          │
│  https://www.olx.uz/nedvizhimost/?page=3                          │
└────────────────────────────────────────────────────────────────────┘
```

## Installation

```bash
# Navigate to crawler directory
cd telegram-ai/crawler-olx

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Environment Setup

Copy and configure the `.env` file:

```bash
cp .env.example .env
```

Required variables in `.env`:

```env
# UcharMarket Backend (auto-push crawled data)
BACKEND_URL=http://localhost:7879

# LLM Provider: 'openai', 'gemini', or 'ollama'
LLM_PROVIDER=ollama

# OpenAI (required if LLM_PROVIDER=openai)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Google Gemini (required if LLM_PROVIDER=gemini)
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash-lite

# Ollama (required if LLM_PROVIDER=ollama — free, no rate limits)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

Get API keys:
- **OpenAI**: https://platform.openai.com/api-keys
- **Gemini**: https://aistudio.google.com/app/apikey
- **Ollama**: No API key needed — runs locally via Docker

## Two Crawler Modes

### 1. `olx_crawler.py` — Full-featured crawler (production)

Uses the shared `LLMExtractor` from `../crawler/` (supports Anthropic, OpenAI, Gemini, and Ollama). Downloads images, saves markdown/JSON locally, and pushes listings to the backend API.

```bash
# Default provider from .env
python olx_crawler.py

# Force a specific provider
python olx_crawler.py --provider openai
python olx_crawler.py --provider gemini
python olx_crawler.py --provider anthropic
python olx_crawler.py --provider ollama

# Crawl specific category
python olx_crawler.py --category apartments
python olx_crawler.py --category apartments_sale

# Crawl a single listing URL
python olx_crawler.py --url https://www.olx.uz/d/obyavlenie/3-honali-kvartira-ID4hiGs.html

# Limit pages
python olx_crawler.py --max-pages 5

# Run with visible browser (for debugging)
python olx_crawler.py --headless=false

# Re-crawl previously processed listings
python olx_crawler.py --force-update

# List available categories
python olx_crawler.py --list-categories
```

### 2. `olx_crawler_n8n.py` — Lightweight crawler (n8n / standalone)

Self-contained crawler with its own LLM extraction. Outputs a single JSON array file. Supports OpenAI, Gemini, and Ollama.

```bash
# Default provider from .env (defaults to gemini)
python olx_crawler_n8n.py

# Force a specific provider
python olx_crawler_n8n.py --provider openai
python olx_crawler_n8n.py --provider gemini
python olx_crawler_n8n.py --provider ollama

# Crawl specific category with limited pages
python olx_crawler_n8n.py --category apartments --max-pages 3

# Custom output file
python olx_crawler_n8n.py --output my_listings.json

# Run with visible browser
python olx_crawler_n8n.py --headless=false
```

## LLM Provider Selection

Provider is selected in this priority order:

1. `--provider` CLI argument (highest priority)
2. `LLM_PROVIDER` environment variable in `.env`
3. Default: `gemini` for n8n crawler, `anthropic` for full crawler

### Supported Providers

| Provider | Models | Cost | Best For |
|----------|--------|------|----------|
| `ollama` | qwen2.5:7b (default), any Ollama model | Free, unlimited | Bulk crawling, no rate limits |
| `gemini` | gemini-2.5-flash-lite (default) | Free (rate-limited) | Light usage |
| `openai` | gpt-4o-mini (default), gpt-4o | Paid | High-quality extraction |
| `anthropic` | claude-3-5-sonnet (default) | Paid | Best quality (full crawler only) |

### Ollama Setup (Docker)

```bash
# Start Ollama container
docker run -d --name ollama -p 11434:11434 \
  -v ollama_data:/root/.ollama \
  --restart unless-stopped ollama/ollama

# Pull a model (qwen2.5:7b recommended for multilingual JSON extraction)
docker exec ollama ollama pull qwen2.5:7b

# Verify it's running
curl http://localhost:11434/api/tags
```

Other good Ollama models for this task:
- `qwen2.5:7b` — Best multilingual + JSON (recommended)
- `llama3.1:8b` — Good general purpose
- `mistral:7b` — Fast, decent quality

## Available Categories

| Category | URL Path |
|----------|----------|
| `all_real_estate` | /nedvizhimost/ |
| `apartments` | /nedvizhimost/kvartiry/ |
| `apartments_sale` | /nedvizhimost/kvartiry/prodazha/ |
| `apartments_rent` | /nedvizhimost/kvartiry/arenda/ |
| `houses` | /nedvizhimost/doma/ |
| `land` | /nedvizhimost/zemlja/ |
| `commercial` | /nedvizhimost/kommercheskie-pomeshcheniya/ |

## Output

### Full crawler (`olx_crawler.py`)

```
output/
├── markdown/           # Intermediate markdown files
│   ├── ID4hiGs.md
│   └── ID4hj2K.md
├── json/               # Extracted JSON data
│   ├── ID4hiGs.json
│   └── ID4hj2K.json
└── images/             # Downloaded listing images
    ├── ID4hiGs/
    │   ├── 1.jpg
    │   └── 2.jpg
    └── ID4hj2K/
        └── 1.jpg
```

### n8n crawler (`olx_crawler_n8n.py`)

Single JSON file:

```
olx_listings.json
```

### JSON Output Example

```json
{
  "property_type": "apartment",
  "listing_type": "rent",
  "price": 800,
  "currency": "USD",
  "rooms": 3,
  "area_sqm": 80,
  "floor": 4,
  "total_floors": 9,
  "district": "Yunusobod",
  "address": "Ц-5, near Korzinka",
  "description": "Сдается 3-комнатная квартира...",
  "amenities": ["мебель", "кондиционер", "интернет"],
  "contact_phone": "+998909564446",
  "images": ["https://..."],
  "olx_id": "ID4hiGs",
  "url": "https://www.olx.uz/d/obyavlenie/...",
  "crawled_at": "2026-03-12T10:30:00",
  "source": "olx_uz"
}
```

## Architecture

```
crawler-olx/
├── olx_crawler.py       # Full Playwright crawler (production)
├── olx_crawler_n8n.py   # Lightweight crawler (n8n/standalone)
├── olx_extractor.py     # LLM extraction wrapper for full crawler
├── html_to_markdown.py  # HTML → Markdown converter
├── backend_push.py      # Push listings to backend API
├── config.py            # Crawl settings (delays, selectors, categories)
├── .env                 # API keys and provider selection
├── requirements.txt     # Python dependencies
├── schemas/             # Data extraction schemas
└── output/              # Crawled data (markdown, json, images)
```

### Shared Components (from `../crawler/`)

| Component | Purpose |
|-----------|---------|
| `llm_extractor.py` | LLM-based data extraction (Anthropic/OpenAI/Gemini) |
| `llm_config.py` | LLM provider configuration and API keys |
| `schema_loader.py` | YAML schema loading |
| `schemas/real_estate.yaml` | Base data extraction schema |

### Data Pipeline

```
OLX.uz HTML page
    │
    ▼
Playwright (browser automation)
    │
    ▼
html_to_markdown.py (clean HTML → structured Markdown)
    │
    ▼
LLM Extractor (OpenAI / Gemini / Anthropic)
    │
    ▼
JSON (normalized, validated)
    │
    ├──► output/json/          (local storage)
    ├──► olx_listings.json     (n8n mode)
    └──► Backend API           (production push)
         POST /api/v1/crawler/olx/import
```

## Seller Profile Crawling

Both crawlers automatically discover and crawl seller profiles:

1. When visiting a listing, the seller's profile link is extracted
2. The crawler visits the seller's profile page
3. All real estate listings from that seller are crawled
4. Non-real-estate listings are filtered out using keyword detection

This significantly increases coverage by finding listings not visible in category pages.

## Configuration

Edit `config.py` to customize crawl behavior:

```python
MAX_PAGES_PER_CATEGORY = 25       # Pages per category
DELAY_BETWEEN_REQUESTS = 1.0      # Seconds between page loads
DELAY_BETWEEN_LISTINGS = 0.5      # Seconds between listings
HEADLESS = True                    # Browser visibility
MAX_SELLER_PROFILE_PAGES = 3      # Max pages per seller profile
```

## Language Support

Fully supports **Russian** and **Uzbek** (Latin and Cyrillic) content:

- HTML → Markdown preserves Unicode text
- All LLM providers understand Russian and Uzbek
- Descriptions are kept in the original language (not translated)
- Enum fields (`property_type`, `listing_type`, `currency`) use English values

## Notes

- OLX.uz uses JavaScript rendering — Playwright is required
- Rate limiting is built-in (configurable delays between requests)
- Duplicate detection prevents re-processing previously crawled listings
- LLM response caching saves API costs for identical content
- Raw markdown files are saved for debugging (full crawler only)
- The `llm_cache/` directory stores cached LLM responses; safe to delete
