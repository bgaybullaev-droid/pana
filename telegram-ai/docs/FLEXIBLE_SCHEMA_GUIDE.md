# Flexible Schema-Based Crawler Guide

## Overview

The flexible schema system allows you to crawl **different types of Telegram channels** with **different data structures**. Each channel type (products, jobs, real estate, etc.) can have its own extraction schema.

## Architecture

```
Channel List → Schema Mapping → Data Extraction → Structured Storage
     ↓               ↓                  ↓                  ↓
electronics_uz → product_listing → {title, price, ...} → Database
jobs_uz       → job_posting     → {job_title, salary, ...} → Database
kvartira_uz   → real_estate     → {property_type, price, ...} → Database
```

## Quick Start

### 1. Create a Schema File

Create a YAML file in `crawler/schemas/` directory:

**Example: `crawler/schemas/product_listing.yaml`**

```yaml
schema_name: product_listing
version: 1.0
description: "Schema for marketplace product listings"

# Channels using this schema
channels:
  - electronics_uz
  - smartphone_market
  - gadgets_tashkent

# Define what data to extract
fields:
  - name: title
    type: string
    required: true
    extraction:
      pattern: "^(.{1,100})"

  - name: price
    type: decimal
    required: true
    extraction:
      patterns:
        - '\$?\s*(\d{1,3}(?:[.,]\d{3})*)\s*(?:sum|USD)?'

  - name: contact_phone
    type: string
    required: false
    extraction:
      patterns:
        - '\+998\s*\d{2}\s*\d{3}\s*\d{2}\s*\d{2}'

# Validation rules
validation:
  require_images: true
  require_text: true
  min_text_length: 20
```

### 2. Run the Flexible Crawler

```bash
cd crawler
python FlexibleCrawler.py
```

The crawler will:
1. Load all schema files from `schemas/` directory
2. Map each channel to its schema
3. Extract data according to each schema's rules
4. Store structured data in the database

### 3. Query Data by Schema Type

```bash
# Get all product listings
curl "http://localhost:5000/api/Crawler/listings?schema_type=product_listing"

# Get all job postings
curl "http://localhost:5000/api/Crawler/listings?schema_type=job_posting"

# Get statistics by schema
curl "http://localhost:5000/api/Crawler/statistics"
```

## Included Schema Examples

### 1. Product Listing Schema (`product_listing.yaml`)

**Use for:** Electronics, gadgets, marketplace items

**Extracted Fields:**
- `title` - Product name
- `description` - Full description
- `price` - Product price
- `currency` - UZS or USD
- `contact_phone` - Seller phone
- `location` - City/district
- `condition` - new/used/refurbished
- `images` - Product photos
- `category` - Auto-categorized (smartphones, laptops, etc.)

**Example Message:**
```
iPhone 15 Pro Max 256GB

Yangi, karobkada
Narx: 12.000.000 sum
Joylashuv: Toshkent, Chilonzor
Tel: +998 90 123 45 67
```

**Extracted Data:**
```json
{
  "title": "iPhone 15 Pro Max 256GB",
  "price": 12000000,
  "currency": "UZS",
  "condition": "new",
  "location": "Toshkent",
  "contact_phone": "+998 90 123 45 67",
  "category": "smartphones"
}
```

### 2. Job Posting Schema (`job_posting.yaml`)

**Use for:** Job vacancies, career opportunities

**Extracted Fields:**
- `job_title` - Position name
- `company_name` - Hiring company
- `description` - Job description
- `salary_min` / `salary_max` - Salary range
- `employment_type` - full_time/part_time/remote/contract
- `experience_years` - Required experience
- `location` - Job location
- `contact_phone` / `contact_email` - Contact info
- `requirements` - List of requirements

**Example Message:**
```
Vacancy: Python Developer

Company: TechUz LLC
Salary: от 5000000 до 10000000 sum
Employment: Full-time, Remote possible
Experience: 3+ years

Requirements:
- Python, Django, FastAPI
- PostgreSQL, Redis
- Docker, Git

Contact: +998 90 123 45 67
```

### 3. Real Estate Schema (`real_estate.yaml`)

**Use for:** Property listings, apartments, houses

**Extracted Fields:**
- `property_type` - apartment/house/commercial/land
- `listing_type` - sale/rent/daily_rent
- `price` - Property price
- `rooms` - Number of rooms
- `area_sqm` - Area in square meters
- `floor` / `total_floors` - Floor information
- `address` - Property address
- `district` - City district
- `amenities` - List of amenities
- `contact_phone` - Contact info

## Creating Custom Schemas

### Step 1: Define Schema Structure

Create `crawler/schemas/your_schema.yaml`:

```yaml
schema_name: your_schema_name
version: 1.0
description: "Description of what this schema is for"

# List channels that use this schema
channels:
  - channel1
  - channel2
  - channel3

# Define fields to extract
fields:
  - name: field_name
    type: string  # or: integer, decimal, text, array, enum, datetime
    required: true  # or false
    description: "What this field represents"
    extraction:
      # How to extract this field (see extraction methods below)
```

### Step 2: Field Types

| Type | Description | Example |
|------|-------------|---------|
| `string` | Short text (< 255 chars) | "iPhone 15" |
| `text` | Long text | Full description |
| `integer` | Whole number | 5, 100, 2024 |
| `decimal` | Decimal number | 999.99, 12000000.50 |
| `enum` | Predefined values | new/used/refurbished |
| `array` | List of items | ["feature1", "feature2"] |
| `datetime` | Date and time | "2024-10-15T10:30:00" |

### Step 3: Extraction Methods

#### Pattern Extraction (Regex)

Extract using regular expressions:

```yaml
- name: price
  type: decimal
  extraction:
    patterns:
      - 'Narx[:\s]+(\d+)'
      - 'Price[:\s]+(\d+)'
      - '\$?(\d{1,3}(?:[.,]\d{3})*)'
```

#### Source Extraction

Extract from message metadata:

```yaml
- name: posted_at
  type: datetime
  extraction:
    source: "message.date"

# Available sources:
# - message.text (full text)
# - message.id (message ID)
# - message.date (timestamp)
# - channel.username (channel name)
# - message.photos (has photos)
```

#### Mapping

Convert extracted values to standard format:

```yaml
- name: condition
  type: enum
  values: [new, used, refurbished]
  extraction:
    patterns:
      - 'yangi|new|новый'
      - 'ishlatilgan|used|б/у'
    mapping:
      'yangi|new|новый': 'new'
      'ishlatilgan|used|б/у': 'used'
```

#### Fallback Extraction

Provide fallback if pattern doesn't match:

```yaml
- name: title
  type: string
  extraction:
    pattern: "^(.{1,100})"
    fallback: "extract_first_line"  # Use first line as title
    default: "Untitled"  # If all else fails
```

### Step 4: Validation Rules

Define message filtering:

```yaml
validation:
  require_images: true  # Skip messages without photos
  require_text: true    # Skip messages without text
  min_text_length: 20   # Minimum text length
  skip_forwards: false  # Skip forwarded messages
  skip_edits: true      # Skip edited messages
```

### Step 5: Post-Processing

Auto-categorize and normalize data:

```yaml
processing:
  normalize_price: true      # Convert price to standard format
  auto_categorize: true      # Auto-categorize by keywords

  categories:
    electronics:
      keywords: [phone, laptop, iphone, samsung]
    furniture:
      keywords: [chair, table, sofa, диван]
    clothing:
      keywords: [shirt, dress, shoes, одежда]
```

## Advanced Examples

### Multi-Language Support

```yaml
- name: listing_type
  type: enum
  values: [sale, rent]
  extraction:
    patterns:
      - 'sotiladi|sale|продается'  # Uzbek, English, Russian
      - 'ijaraga|rent|аренда'
    mapping:
      'sotiladi|sale|продается': 'sale'
      'ijaraga|rent|аренда': 'rent'
```

### Extracting Lists

```yaml
- name: features
  type: array
  extraction:
    section_markers:
      - 'Features|Imkoniyatlar|Возможности'
    list_patterns:
      - '[-•*]\s*(.+?)(?:\n|$)'
```

### Complex Price Extraction

```yaml
- name: price
  type: decimal
  extraction:
    patterns:
      # Handles: 1000000, 1.000.000, $1,000, 1000 sum
      - '\$?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:sum|сум|USD|so\'m)?'
      - 'Narx[:\s]+(\d+)'
      - 'Price[:\s]+(\d+)'
    unit_patterns:
      - 'sum|сум|so\'m'
      - 'USD|\$'
```

## Testing Your Schema

### 1. Test Schema Loading

```bash
cd crawler
python schema_loader.py
```

This will show:
- All loaded schemas
- Channel-to-schema mappings
- Test extraction example

### 2. Query by Schema Type

```bash
# Start the flexible API
cd api
python server_flexible.py

# Query specific schema
curl "http://localhost:5000/api/Crawler/listings?schema_type=product_listing"
```

### 3. View Statistics

```bash
curl "http://localhost:5000/api/Crawler/statistics"
```

Output:
```json
{
  "total_listings": 150,
  "schema_breakdown": [
    {"schema_type": "product_listing", "count": 80},
    {"schema_type": "job_posting", "count": 45},
    {"schema_type": "real_estate", "count": 25}
  ]
}
```

## File Structure

```
telegram-ai/
├── crawler/
│   ├── FlexibleCrawler.py        # Main crawler with schema support
│   ├── schema_loader.py          # Schema loading and extraction
│   ├── config.py                 # Telegram credentials
│   └── schemas/                  # Schema definitions
│       ├── product_listing.yaml  # Product schema
│       ├── job_posting.yaml      # Job schema
│       ├── real_estate.yaml      # Real estate schema
│       └── your_custom.yaml      # Add your own!
│
├── api/
│   ├── server_flexible.py        # Flexible schema API
│   └── requirements.txt
│
└── uploads/                      # Uploaded images
```

## Database Schema

The flexible system uses a dynamic structure:

**listings** table:
- `id` - Primary key
- `schema_type` - Which schema (product_listing, job_posting, etc.)
- `channel_username` - Source channel
- `message_id` - Telegram message ID
- `raw_data` - Original message text
- `extracted_data` - JSON with extracted fields (schema-specific)
- `created_at` - Timestamp

**listing_images** table:
- `id` - Primary key
- `listing_id` - Foreign key to listings
- `image_path` - File path
- `original_filename` - Original name
- `file_size` - Size in bytes

## API Endpoints

### Create Listing

```bash
POST /api/Crawler
Content-Type: application/json

{
  "schema_type": "product_listing",
  "channel_username": "electronics_uz",
  "message_id": 12345,
  "raw_data": "Original message text...",
  "extracted_data": {
    "title": "iPhone 15",
    "price": 12000000,
    "currency": "UZS"
  }
}
```

### Get Listings (Filtered by Schema)

```bash
GET /api/Crawler/listings?schema_type=product_listing&page=1&per_page=10
```

### Get Statistics

```bash
GET /api/Crawler/statistics
```

Returns breakdown by schema type.

### Upload Images

```bash
POST /api/Crawler/listing/images
Content-Type: multipart/form-data

listingId=123
ListingImages=<file>
```

## Best Practices

1. **One Schema Per Channel Type**
   - Don't mix product and job channels in the same schema
   - Each schema should have a clear, single purpose

2. **Use Descriptive Field Names**
   - Good: `job_title`, `salary_min`, `property_type`
   - Bad: `field1`, `data`, `info`

3. **Support Multiple Languages**
   - Include patterns for Uzbek, Russian, and English
   - Use case-insensitive matching

4. **Test Extraction Patterns**
   - Use real message examples
   - Test with `schema_loader.py` before deploying

5. **Require Critical Fields**
   - Mark essential fields as `required: true`
   - Validation will skip incomplete messages

6. **Use Auto-Categorization**
   - Define keyword-based categories
   - Helps organize large datasets

## Troubleshooting

**Schema not loading:**
- Check YAML syntax (use online validator)
- Ensure `schema_name` field exists
- Check file is in `crawler/schemas/` directory

**Data not extracting:**
- Test regex patterns with real messages
- Check pattern escaping (use raw strings)
- Enable verbose logging in crawler

**Channel not being processed:**
- Verify channel is listed in schema's `channels` array
- Check channel username matches (without @)
- Ensure API server is running

## Next Steps

1. ✅ Create your custom schema YAML files
2. ✅ Add your channels to the `channels` array
3. ✅ Test extraction with `python schema_loader.py`
4. ✅ Start flexible API: `python api/server_flexible.py`
5. ✅ Start crawler: `python crawler/FlexibleCrawler.py`
6. ✅ Subscribe bot to your channels
7. ✅ Monitor data at http://localhost:5000

---

**Questions?** Check existing schemas for examples or modify them for your needs!
