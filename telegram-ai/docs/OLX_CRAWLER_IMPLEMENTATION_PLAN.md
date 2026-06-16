# OLX.uz Crawler Implementation Plan

> **Status:** ✅ Implemented
> **Date:** February 2026
> **Purpose:** Convert OLX.uz HTML listings to structured JSON via Markdown intermediate format
> **Location:** `telegram-ai/crawler-olx/`

---

## How The Crawler Works

### Step-by-Step Flow

```
┌────────────────────────────────────────────────────────────────────┐
│  STEP 1: Go to category page                                       │
│  https://www.olx.uz/nedvizhimost/                                  │
│                                                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ Listing  │ │ Listing  │ │ Listing  │ │ Listing  │  ... (many)  │
│  │  Card 1  │ │  Card 2  │ │  Card 3  │ │  Card 4  │              │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘              │
│       │            │            │            │                     │
│       ▼            ▼            ▼            ▼                     │
│     URL 1        URL 2        URL 3        URL 4                   │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│  STEP 2: Collect all listing URLs from the page                    │
│                                                                    │
│  - /d/obyavlenie/3-honali-kvartira-sotiladi-ID4hiGs.html          │
│  - /d/obyavlenie/kvartira-mirobod-tuman-ID4hj2K.html              │
│  - /d/obyavlenie/2-xonali-uy-chilonzor-ID4hk8M.html               │
│  - ... (30-40 URLs per page)                                       │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│  STEP 3: Enter EACH listing URL, one by one                        │
│                                                                    │
│  Example: https://www.olx.uz/d/obyavlenie/3-honali-kvartira-sotiladi-ID4hiGs.html
│                              │                                     │
│                              ▼                                     │
│                    ┌─────────────────┐                             │
│                    │  Get HTML       │  (full page source)         │
│                    └────────┬────────┘                             │
│                              ▼                                     │
│                    ┌─────────────────┐                             │
│                    │  Convert to     │  (clean text)               │
│                    │  Markdown       │                             │
│                    └────────┬────────┘                             │
│                              ▼                                     │
│                    ┌─────────────────┐                             │
│                    │  Extract to     │  (structured data)          │
│                    │  JSON           │                             │
│                    └─────────────────┘                             │
│                                                                    │
│  Then go to next listing URL, repeat...                            │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│  STEP 4: Go to next page of listings, repeat                       │
│                                                                    │
│  https://www.olx.uz/nedvizhimost/?page=2                          │
│  https://www.olx.uz/nedvizhimost/?page=3                          │
│  ...                                                               │
└────────────────────────────────────────────────────────────────────┘
```

### Two Types of Pages

| Page Type | URL Pattern | What It Contains |
|-----------|-------------|------------------|
| **Category Page** | `https://www.olx.uz/nedvizhimost/` | List of listing cards (30-40 per page) |
| **Listing Page** | `https://www.olx.uz/d/obyavlenie/...-ID{xxxxx}.html` | One listing with full details |

### The Conversion Pipeline

For each listing page:

```
HTML → Markdown → JSON
```

1. **HTML**: Raw page source from the listing URL
2. **Markdown**: Clean text with structure preserved (Russian/Uzbek intact)
3. **JSON**: Structured data ready for database

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         OLX.uz CRAWLER                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐ │
│  │ Playwright │──▶│  HTML to   │──▶│    LLM     │──▶│   Output   │ │
│  │  Fetcher   │   │  Markdown  │   │ Extractor  │   │ JSON/CSV   │ │
│  └────────────┘   └────────────┘   └────────────┘   └────────────┘ │
│        │                                                    │       │
│        ▼                                                    ▼       │
│   Dynamic JS                                           Structured   │
│   Rendering                                            Data         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
telegram-ai/
├── crawler/                    # Existing Telegram crawler
│   ├── llm_extractor.py       # REUSE - works for any text
│   ├── llm_config.py          # REUSE - LLM settings
│   ├── vector_db.py           # REUSE - duplicate detection
│   ├── image_embeddings.py    # REUSE - CLIP embeddings
│   └── schemas/
│       └── real_estate.yaml   # REUSE - same schema
│
└── crawler-olx/                # NEW - OLX.uz crawler
    ├── config.py              # OLX-specific settings
    ├── sites_config.yaml      # Target URLs and selectors
    ├── olx_crawler.py         # Main crawler (Playwright)
    ├── html_to_markdown.py    # HTML → Markdown converter
    ├── olx_extractor.py       # Wrapper for LLM extractor
    ├── requirements.txt       # Dependencies
    ├── README.md              # Documentation
    │
    ├── schemas/
    │   └── olx_real_estate.yaml   # OLX-specific schema
    │
    └── output/
        ├── markdown/          # Converted markdown files
        ├── json/              # Extracted JSON data
        └── images/            # Downloaded images
```

---

## Component Mapping (Telegram → OLX)

| Telegram Crawler | OLX Crawler | Purpose |
|------------------|-------------|---------|
| `FlexibleCrawlerWithHistory.py` | `olx_crawler.py` | Main crawler loop |
| `Telethon` client | `Playwright` browser | Fetch content |
| `message.text` | `html_to_markdown()` | Get text content |
| `llm_extractor.py` | **REUSE** | Extract JSON from text |
| `vector_db.py` | **REUSE** | Duplicate detection |
| `image_embeddings.py` | **REUSE** | Image similarity |
| `schemas/real_estate.yaml` | **REUSE** or extend | Data schema |
| `channels_config.yaml` | `sites_config.yaml` | Target sources |

---

## Module Specifications

### 1. `config.py` - Configuration

```python
# Settings to define:
OLX_BASE_URL = "https://www.olx.uz"
CATEGORIES = {
    "apartments": "/nedvizhimost/kvartiry/",
    "houses": "/nedvizhimost/doma/",
    "land": "/nedvizhimost/zemlja/",
    "commercial": "/nedvizhimost/kommercheskie-pomeshcheniya/"
}
MAX_PAGES_PER_CATEGORY = 25
DELAY_BETWEEN_REQUESTS = 1.0  # seconds
OUTPUT_DIR = "./output"
```

### 2. `sites_config.yaml` - Target Configuration

```yaml
source:
  name: "olx_uz"
  base_url: "https://www.olx.uz"
  language: "ru"  # or "uz"

# URL patterns
urls:
  # Category page (shows list of listings)
  category_page: "https://www.olx.uz/nedvizhimost/"

  # Listing page pattern (individual listing)
  # Example: https://www.olx.uz/d/obyavlenie/3-honali-kvartira-sotiladi-ID4hiGs.html
  listing_pattern: "/d/obyavlenie/*-ID*.html"

  # Pagination
  pagination: "?page={page}"
  max_pages: 25

# Categories to crawl
targets:
  - name: "all_real_estate"
    path: "/nedvizhimost/"

  - name: "apartments"
    path: "/nedvizhimost/kvartiry/"

  - name: "houses"
    path: "/nedvizhimost/doma/"

# Selectors for category page (to find listing URLs)
selectors:
  category_page:
    listing_cards: '[data-cy="l-card"]'
    listing_link: 'a[href*="/d/obyavlenie/"]'
    next_page: '[data-testid="pagination-forward"]'

  # Selectors for listing page (to extract content)
  listing_page:
    title: 'h4[data-cy="ad_title"]'
    price: '[data-testid="ad-price-container"]'
    description: '[data-cy="ad_description"]'
    parameters: '[data-testid="ad-parameters"]'
    location: '[data-testid="ad-location"]'
    seller: '[data-testid="seller-card"]'
    images: '[data-cy="gallery"] img'

filters:
  require_images: true
  min_price: 1000  # USD
  max_price: 10000000
```

### 3. `html_to_markdown.py` - Converter

**Purpose:** Convert OLX HTML to clean Markdown

**Method:** Use `markdownify` (Python) or Turndown (JS) via subprocess

**Input:** Raw HTML string from Playwright

**Output:** Clean Markdown string

**Functions:**
```python
def convert_listing_page(html: str) -> str:
    """Convert full HTML page to Markdown"""
    pass

def extract_main_content(html: str) -> str:
    """Remove nav, ads, footer - keep main content only"""
    pass

def clean_markdown(md: str) -> str:
    """Remove empty lines, normalize whitespace"""
    pass
```

**Conversion Rules:**
- Strip `<script>`, `<style>`, `<nav>`, `<footer>`, `<iframe>`
- Preserve `<h1>`-`<h6>` → `#` headings
- Preserve `<ul>`, `<ol>` → `-` lists
- Preserve `<a href>` → `[text](url)`
- Preserve `<table>` → GFM tables
- Extract `<img src>` URLs separately

### 4. `olx_crawler.py` - Main Crawler

**Class:** `OLXCrawler`

**Methods:**

```python
class OLXCrawler:
    def __init__(self):
        """
        - Initialize Playwright browser
        - Load sites_config.yaml
        - Initialize LLM extractor (from ../crawler/)
        - Initialize vector DB (from ../crawler/)
        """
        pass

    async def get_listing_urls(self, category_url: str) -> list:
        """
        STEP 1: Go to category page, collect all listing URLs

        Example:
          Input:  https://www.olx.uz/nedvizhimost/
          Output: [
            "https://www.olx.uz/d/obyavlenie/3-honali-kvartira-ID4hiGs.html",
            "https://www.olx.uz/d/obyavlenie/kvartira-mirobod-ID4hj2K.html",
            ...
          ]
        """
        pass

    async def crawl_listing(self, listing_url: str) -> dict:
        """
        STEP 2: Enter one listing URL and convert HTML → Markdown → JSON

        Example:
          Input:  https://www.olx.uz/d/obyavlenie/3-honali-kvartira-ID4hiGs.html

          Process:
            1. page.goto(listing_url)
            2. html = page.content()
            3. markdown = html_to_markdown(html)
            4. json_data = llm_extractor.extract(markdown)

          Output: {
            "property_type": "apartment",
            "price": 800,
            "rooms": 3,
            ...
          }
        """
        pass

    async def crawl_category(self, category_url: str):
        """
        Combine steps 1 and 2:
          1. Get all listing URLs from category page
          2. For each URL, crawl the listing
          3. Handle pagination (page 1, 2, 3...)
        """
        pass

    async def save_results(self, data: dict, listing_id: str):
        """
        Save extracted data:
          - output/json/ID4hiGs.json
          - output/images/ID4hiGs_1.jpg
        """
        pass

    async def run(self):
        """
        Main entry point:
          1. Go to https://www.olx.uz/nedvizhimost/
          2. Collect listing URLs
          3. Enter each listing, convert HTML → Markdown → JSON
          4. Go to next page, repeat
        """
        pass
```

**Crawl Flow:**
```
1. Load configuration

2. Go to category page: https://www.olx.uz/nedvizhimost/

3. On category page:
   a. Find all listing cards
   b. Extract each listing URL (e.g., /d/obyavlenie/...-ID4hiGs.html)
   c. Store URLs in a list

4. For each listing URL in the list:
   a. Go to: https://www.olx.uz/d/obyavlenie/...-ID4hiGs.html
   b. Wait for page to load
   c. Get HTML: page.content()
   d. Convert: HTML → Markdown
   e. Extract: Markdown → JSON (via LLM)
   f. Download images
   g. Check for duplicates
   h. Save JSON to output

5. After all listings on page 1 done:
   a. Go to page 2: https://www.olx.uz/nedvizhimost/?page=2
   b. Repeat steps 3-4

6. Continue until max_pages reached

7. Output final stats
```

### 5. `olx_extractor.py` - LLM Wrapper

**Purpose:** Wrapper around existing `llm_extractor.py`

**Modifications needed:**
- Add OLX-specific pre-processing
- Clean Markdown before sending to LLM
- Add OLX-specific few-shot examples

**Functions:**
```python
def extract_from_markdown(markdown: str, schema: dict) -> dict:
    """Main extraction function"""
    pass

def preprocess_olx_content(markdown: str) -> str:
    """Clean and prepare OLX content"""
    pass

def postprocess_extraction(data: dict) -> dict:
    """Normalize extracted data"""
    pass
```

### 6. `schemas/olx_real_estate.yaml` - Schema Extension

```yaml
# Extends existing real_estate.yaml with OLX-specific fields
schema_name: olx_real_estate
version: 1.0
extends: real_estate  # Inherit base schema

# OLX-specific fields
additional_fields:
  - name: olx_id
    type: string
    description: "OLX listing ID (from URL)"

  - name: seller_type
    type: enum
    values: [business, private]

  - name: views_count
    type: integer
    description: "Number of views on listing"

  - name: posted_date
    type: datetime
    description: "When listing was posted"

  - name: last_updated
    type: datetime
    description: "When listing was last updated"

# OLX URL patterns
url_patterns:
  listing: "/d/obyavlenie/{slug}-ID{id}.html"
  category: "/nedvizhimost/{subcategory}/"
```

---

## Dependencies

```
# requirements.txt
playwright>=1.40.0
markdownify>=0.11.6      # HTML to Markdown (Python)
beautifulsoup4>=4.12.0   # HTML parsing
pyyaml>=6.0              # Config files
requests>=2.31.0         # HTTP client
tqdm>=4.66.0             # Progress bars

# Shared with Telegram crawler (already installed):
# anthropic, openai, chromadb, sentence-transformers, torch, Pillow
```

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│  CATEGORY PAGE                                                    │
│  https://www.olx.uz/nedvizhimost/                                │
│                                                                   │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                     │
│  │ Card 1 │ │ Card 2 │ │ Card 3 │ │ Card 4 │  ...                │
│  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘                     │
│      │          │          │          │                           │
│      ▼          ▼          ▼          ▼                           │
│   URL 1      URL 2      URL 3      URL 4                          │
└──────────────────────────┬───────────────────────────────────────┘
                           │ Collect all URLs
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  LISTING URLs COLLECTED                                           │
│                                                                   │
│  - https://www.olx.uz/d/obyavlenie/3-honali-kvartira-ID4hiGs.html│
│  - https://www.olx.uz/d/obyavlenie/kvartira-mirobod-ID4hj2K.html │
│  - https://www.olx.uz/d/obyavlenie/2-xonali-uy-ID4hk8M.html      │
│  - ... (30-40 URLs)                                               │
└──────────────────────────┬───────────────────────────────────────┘
                           │ Enter each URL
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  LISTING PAGE (one at a time)                                     │
│  https://www.olx.uz/d/obyavlenie/3-honali-kvartira-ID4hiGs.html  │
└──────────────────────────┬───────────────────────────────────────┘
                           │ page.content()
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  RAW HTML (Russian/Uzbek)                                         │
│                                                                   │
│  <h4>Ц-5 рядом Корзинка Пр-т Шарафа Рашидова...</h4>             │
│  <p>Количество комнат: 3</p>                                     │
│  <p>Общая площадь: 80</p>                                        │
│  <p>Цена: 800 у.е.</p>                                           │
└──────────────────────────┬───────────────────────────────────────┘
                           │ html_to_markdown.py
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  CLEAN MARKDOWN                                                   │
│                                                                   │
│  # Ц-5 рядом Корзинка Пр-т Шарафа Рашидова...                    │
│                                                                   │
│  **Количество комнат:** 3                                        │
│  **Общая площадь:** 80                                           │
│  **Цена:** 800 у.е.                                              │
└──────────────────────────┬───────────────────────────────────────┘
                           │ llm_extractor.py
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  STRUCTURED JSON                                                  │
│                                                                   │
│  {                                                                │
│    "property_type": "apartment",                                 │
│    "listing_type": "rent",                                       │
│    "price": 800,                                                 │
│    "currency": "USD",                                            │
│    "rooms": 3,                                                   │
│    "area_sqm": 80,                                               │
│    "district": "Yunusobod",                                      │
│    "address": "Ц-5, near Korzinka",                              │
│    "contact_phone": "+998909564446"                              │
│  }                                                                │
└──────────────────────────┬───────────────────────────────────────┘
                           │ Save
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  OUTPUT                                                           │
│                                                                   │
│  - output/json/ID4hiGs.json                                      │
│  - output/images/ID4hiGs_1.jpg                                   │
│  - output/images/ID4hiGs_2.jpg                                   │
└──────────────────────────────────────────────────────────────────┘
                           │
                           ▼
              Go to next listing URL, repeat...
              Then go to page 2, page 3, etc.
```

---

## Language Support

The pipeline fully supports **Russian** and **Uzbek** content:

### Why It Works

1. **Markdown preserves Unicode** - Russian/Uzbek text stays intact during HTML→MD conversion
2. **Claude/GPT are multilingual** - They understand Russian and Uzbek fluently
3. **Existing extractor is trained** - 13 real examples from Uzbekistan channels already in `llm_extractor.py`

### Vocabulary Mappings (Already Implemented)

| Russian | Uzbek | English | JSON Field |
|---------|-------|---------|------------|
| продается | sotiladi | for sale | `listing_type: "sale"` |
| аренда | ijaraga | for rent | `listing_type: "rent"` |
| комнат | xona | rooms | `rooms: 3` |
| квартира | kvartira | apartment | `property_type: "apartment"` |
| этаж | qavat | floor | `floor: 4` |
| у.е. / $ | dollar | USD | `currency: "USD"` |
| сум | so'm | UZS | `currency: "UZS"` |

---

## Execution Commands

```bash
# Install dependencies
cd telegram-ai/crawler-olx
pip install -r requirements.txt
playwright install chromium

# Run crawler (all categories)
python olx_crawler.py

# Run specific category
python olx_crawler.py --category apartments_sale

# Run with page limit
python olx_crawler.py --max-pages 5

# Run with visible browser (debugging)
python olx_crawler.py --headless=false

# Export to CSV
python olx_crawler.py --output-format csv
```

---

## Reusable Components (No Changes Needed)

| Component | Path | Why Reusable |
|-----------|------|--------------|
| `llm_extractor.py` | `crawler/` | Already handles Russian/Uzbek |
| `llm_config.py` | `crawler/` | Same LLM settings |
| `vector_db.py` | `crawler/` | Same duplicate detection |
| `image_embeddings.py` | `crawler/` | Same CLIP model |
| `real_estate.yaml` | `crawler/schemas/` | Same data fields |

---

## Implementation Phases

### Phase 1: Setup
- Create folder structure
- Create `config.py` and `sites_config.yaml`
- Create `requirements.txt`

### Phase 2: HTML to Markdown
- Implement `html_to_markdown.py`
- Test with sample OLX pages
- Verify Russian/Uzbek text preserved

### Phase 3: Crawler Core
- Implement `olx_crawler.py`
- Add pagination handling
- Add rate limiting

### Phase 4: Integration
- Connect to existing `llm_extractor.py`
- Connect to `vector_db.py`
- Test full pipeline

### Phase 5: Output
- JSON export
- CSV export
- Image download

---

## OLX.uz Page Structure (From Analysis)

### Listing Page Elements

| Element | Selector | Content |
|---------|----------|---------|
| Title | `h4[data-cy="ad_title"]` | Listing title |
| Price | `h3` (price container) | "800 у.е." |
| Images | Carousel groups | 12 images |
| Parameters | Parameter list | Rooms, area, floor, etc. |
| Description | Description div | Full text |
| Seller | Seller card | Name, member since, online status |
| Location | Location section | District, city, region |

### Property Parameters Available

- Количество комнат (Number of rooms)
- Общая площадь (Total area)
- Этаж (Floor)
- Этажность дома (Building floors)
- Тип строения (Building type)
- Планировка (Layout)
- Санузел (Bathroom)
- Меблирована (Furnished)
- Высота потолков (Ceiling height)
- В квартире есть (Amenities)
- Рядом есть (Nearby)
- Ремонт (Renovation)
- Комиссионные (Commission)

---

## Notes

- OLX.uz uses JavaScript rendering - Playwright is required
- Rate limiting recommended: 1 second between requests
- Respect robots.txt and terms of service
- Store raw Markdown for debugging/reprocessing
