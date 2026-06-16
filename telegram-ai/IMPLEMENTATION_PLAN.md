# Implementation Plan: Real Estate Crawler CSV Export + Docs Cleanup

## Overview

Two tasks to complete:
1. **CSV Export Feature** - Modify crawler to export real estate listings to CSV
2. **Documentation Cleanup** - Organize/delete redundant docs

---

## PART 1: CSV Export Feature

### Goal
Create a crawler that:
- Connects to Telegram and crawls 14 configured real estate channels
- Uses LLM (Claude) to extract structured data from messages
- Saves extracted data to CSV file
- Downloads and saves property images locally

### Current Codebase (Reference Files)

| File | Purpose |
|------|---------|
| `crawler/FlexibleCrawlerWithHistory.py` | Existing crawler - use as reference |
| `crawler/schemas/real_estate.yaml` | Schema with 14 channels + field definitions |
| `crawler/llm_extractor.py` | LLM extraction logic |
| `crawler/schema_loader.py` | Loads YAML schemas |
| `crawler/config.py` | Telegram credentials |
| `crawler/llm_config.py` | LLM settings, `PROCESS_HISTORICAL_MESSAGES` var |

### Files to Create

#### 1. `crawler/csv_exporter.py`
Utility class for CSV operations:
- Initialize CSV file with headers
- Auto-increment listing IDs
- Save images to `output/images/` folder
- Append rows to CSV with thread-safe locking
- Clean text (remove newlines, limit length)

#### 2. `crawler/RealEstateCrawlerCSV.py`
Main crawler script:
- Connect to Telegram using Telethon
- Load channels from `schemas/real_estate.yaml`
- For each channel, fetch N historical messages
- Filter: must have photo + text (min 10 chars)
- Extract data using `LLMExtractor`
- Save to CSV using `CSVExporter`
- Download images to local folder
- Print summary stats at end

### CSV Schema (Output Columns)

```csv
listing_id,channel,message_id,timestamp,property_type,listing_type,price,currency,rooms,area_sqm,floor,total_floors,district,address,description,contact_phone,amenities,image_paths,raw_text
```

| Column | Type | Source |
|--------|------|--------|
| `listing_id` | int | Auto-generated (1, 2, 3...) |
| `channel` | string | Telegram channel username |
| `message_id` | int | Telegram message ID |
| `timestamp` | ISO datetime | Message date |
| `property_type` | enum | LLM extracted: apartment/house/commercial/land/office |
| `listing_type` | enum | LLM extracted: sale/rent/daily_rent |
| `price` | decimal | LLM extracted |
| `currency` | enum | LLM extracted: UZS/USD |
| `rooms` | int | LLM extracted |
| `area_sqm` | decimal | LLM extracted |
| `floor` | int | LLM extracted |
| `total_floors` | int | LLM extracted |
| `district` | string | LLM extracted |
| `address` | string | LLM extracted |
| `description` | text | LLM extracted (cleaned) |
| `contact_phone` | string | LLM extracted |
| `amenities` | string | LLM extracted (comma-separated) |
| `image_paths` | string | Local paths (semicolon-separated) |
| `raw_text` | text | Original message text (cleaned) |

### Output Structure

```
crawler/
├── output/
│   ├── real_estate_listings.csv
│   └── images/
│       ├── listing_00001_img_1.jpg
│       ├── listing_00002_img_1.jpg
│       └── ...
```

### Key Implementation Notes

1. **Remove API calls** - Don't POST to `localhost:5000`, just save to CSV
2. **Remove vector DB** - No need for `VectorDatabase`, `ImageEmbedder`
3. **Keep LLM extraction** - Use `LLMExtractor` for structured data extraction
4. **Image naming** - Use format `listing_{ID:05d}_img_{N}.jpg`
5. **Handle albums** - If message has multiple photos, save all with index
6. **Rate limiting** - Add 0.5-1 second delay between messages
7. **Resume support** - Check existing CSV for last listing_id on startup

### Channels to Crawl (from real_estate.yaml)

```
baburieltor, realtor_alii, UyCharxiy9, Kvartira_doma_Tashkent,
Nedvijimosss, uybozor_realtor, realtor_yunusov, grandestate2019,
RealestTash, vitrinanedvizhimosti, arentash, Imkonuyjoysavdoo,
ANDIJON_UYJOY, NAMANGAN_UYJOY_BOZORI
```

### Usage Example

```bash
cd crawler
python RealEstateCrawlerCSV.py                    # Default: 10 msgs/channel
python RealEstateCrawlerCSV.py -n 50              # 50 msgs/channel
python RealEstateCrawlerCSV.py -o my_output       # Custom output dir
```

---

## PART 2: Documentation Cleanup

### Current State (16 .md files in root)

### Files to KEEP in Root (2 files)
- `CLAUDE.md` - Claude Code instructions (required)
- `README.md` - Project overview (standard)

### Files to MOVE to `/docs` (8 files)
Create `docs/` folder and move:
1. `SETUP.md`
2. `GETTING_STARTED.md`
3. `ENV_SETUP_GUIDE.md`
4. `DASHBOARD_GUIDE.md`
5. `FLEXIBLE_SCHEMA_GUIDE.md`
6. `LLM_CRAWLER_GUIDE.md`
7. `HISTORICAL_PROCESSING.md`
8. `SINGLE_MODEL_CONFIGURATION.md`

### Files to DELETE (6 files - redundant/duplicate)
1. `README_LLM.md` - Duplicate of README.md
2. `QUICK_START_LLM.md` - Redundant with GETTING_STARTED.md
3. `QUICK_START_DASHBOARD.md` - Redundant with DASHBOARD_GUIDE.md
4. `QUICK_START_TESTING.md` - Redundant with HISTORICAL_PROCESSING.md
5. `LLM_IMPLEMENTATION_SUMMARY.md` - Outdated implementation notes
6. `CHANGELOG_SINGLE_MODEL.md` - One-time changelog entry

### Final Structure

```
telegram-ai/
├── CLAUDE.md                    # Keep
├── README.md                    # Keep
├── docs/
│   ├── SETUP.md
│   ├── GETTING_STARTED.md
│   ├── ENV_SETUP_GUIDE.md
│   ├── DASHBOARD_GUIDE.md
│   ├── FLEXIBLE_SCHEMA_GUIDE.md
│   ├── LLM_CRAWLER_GUIDE.md
│   ├── HISTORICAL_PROCESSING.md
│   └── SINGLE_MODEL_CONFIGURATION.md
└── crawler/
    └── README.md                # Already exists
```

### Commands to Execute

```bash
# Create docs folder
mkdir docs

# Move files
mv SETUP.md docs/
mv GETTING_STARTED.md docs/
mv ENV_SETUP_GUIDE.md docs/
mv DASHBOARD_GUIDE.md docs/
mv FLEXIBLE_SCHEMA_GUIDE.md docs/
mv LLM_CRAWLER_GUIDE.md docs/
mv HISTORICAL_PROCESSING.md docs/
mv SINGLE_MODEL_CONFIGURATION.md docs/

# Delete redundant files
rm README_LLM.md
rm QUICK_START_LLM.md
rm QUICK_START_DASHBOARD.md
rm QUICK_START_TESTING.md
rm LLM_IMPLEMENTATION_SUMMARY.md
rm CHANGELOG_SINGLE_MODEL.md
```

### Update README.md Links
After moving, update any documentation links in `README.md` to point to `docs/` folder.

---

## Execution Order

1. **Docs cleanup first** (quick win, 5 mins)
2. **CSV exporter utility** (create csv_exporter.py)
3. **Main crawler script** (create RealEstateCrawlerCSV.py)
4. **Test with small batch** (-n 5)
5. **Full crawl** (-n 50 or more)

---

## Dependencies

Already in `crawler/requirements.txt`:
- telethon
- pyyaml
- anthropic (for LLM)

No new dependencies needed - just uses standard `csv` module.

---

## Success Criteria

- [ ] CSV file created with all columns populated
- [ ] Images downloaded and properly named
- [ ] 14 channels successfully crawled
- [ ] LLM extraction working for Uzbek/Russian text
- [ ] Docs organized in `/docs` folder
- [ ] Redundant docs deleted
