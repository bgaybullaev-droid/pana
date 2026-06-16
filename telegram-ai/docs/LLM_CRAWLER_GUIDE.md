# LLM-Powered Crawler with Image Similarity Search

## Overview

This is a **production-grade** Telegram crawler that uses:

1. **LLM (Claude/GPT)** - Extract structured data from diverse posting styles (no regex!)
2. **CLIP** - Generate image embeddings for similarity search (FREE, runs locally)
3. **ChromaDB** - Vector database for finding duplicate images (like Instagram)
4. **Sentence Transformers** - Text embeddings for duplicate text detection

## Why This Approach?

### ❌ Pattern Matching (Old Approach)
- Fails with varied posting formats
- Breaks when channels change style
- Can't handle typos or variations
- Requires manual regex for each language

### ✅ LLM-Based (New Approach)
- Handles ANY posting format
- Multi-language support (Uzbek, Russian, English)
- Extracts semantic meaning, not just text patterns
- Adapts to different writing styles automatically

### 💰 Cost-Effective Design

| Component | Cost | Why It's Cheap |
|-----------|------|----------------|
| **Text Extraction** | ~$0.003/message | Only for extraction, not search |
| **Image Embeddings** | FREE | CLIP runs locally on your machine |
| **Text Embeddings** | FREE | Sentence Transformers runs locally |
| **Vector Search** | FREE | ChromaDB is open source |
| **Storage** | FREE | SQLite database |

**Total: ~$3-5 per 1000 messages** (only LLM costs)

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  Telegram Message                                            │
│  "3-xonali kvartira Chilonzorda                             │
│   Narxi: 120.000$ kelishamiz                                │
│   80m², 5/9-qavat, evro ta'mir                              │
│   Tel: +998901234567"                                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────┴─────────────────┐
        │                                    │
        ▼                                    ▼
┌──────────────────┐              ┌──────────────────┐
│  LLM Extraction  │              │  Image Download  │
│  (Claude/GPT)    │              │  (Telegram API)  │
└──────────────────┘              └──────────────────┘
        │                                    │
        ▼                                    ▼
   Structured Data                  ┌──────────────────┐
   {                                │  CLIP Embedding  │
     "property_type": "apartment",  │  (512-dim vector)│
     "rooms": 3,                    └──────────────────┘
     "price": 120000,                        │
     "district": "Chilonzor",                ▼
     "area_sqm": 80,              ┌──────────────────────┐
     "floor": 5                   │  Vector DB Search    │
   }                              │  (Find Similar)      │
        │                         └──────────────────────┘
        ▼                                    │
┌────────────────────┐                      ▼
│  Duplicate Check   │←──────────  Image Similarity: 0.92
│  (Vector Search)   │
└────────────────────┘
        │
        ▼
   ┌─────────────────┐
   │  Is Duplicate?  │
   │  Yes: Skip/Flag │
   │  No: Store      │
   └─────────────────┘
```

## Architecture

### 1. LLM Extraction (`llm_extractor.py`)

**Schema-Aware Prompts:**
```python
# The system builds intelligent prompts for each schema
prompt = f"""
Extract structured data from this real estate listing:

REQUIRED FIELDS:
  - property_type (apartment/house/commercial)
  - price (number only, no currency symbols)
  - rooms (integer)

BE FLEXIBLE:
  - "3-xonali", "3 rooms", "3-комнатная" → rooms: 3
  - "120.000$", "$120k", "120 ming" → price: 120000

MESSAGE: {message_text}
"""
```

**Why It Works:**
- LLM understands context and variations
- Extracts semantic meaning, not exact matches
- Handles typos, abbreviations, multiple languages
- No regex maintenance

### 2. Image Similarity (`image_embeddings.py`)

**CLIP Model:**
```python
# Convert image to 512-dimensional vector
embedder = ImageEmbedder()
embedding = embedder.embed_image('photo.jpg')
# embedding shape: (512,) - a fingerprint of the image
```

**How CLIP Works:**
- Trained on 400M image-text pairs
- Creates semantic understanding of images
- Similar images → similar vectors
- Fast: ~100ms per image on GPU, ~500ms on CPU

**Instagram's Approach:**
Instagram uses similar technology:
1. Extract image features (embeddings)
2. Store in vector database
3. Compare new images to database
4. Flag if similarity > threshold (e.g., 0.88)

### 3. Vector Database (`vector_db.py`)

**ChromaDB for Similarity Search:**
```python
# Add image to database
db.add_image_embedding(
    listing_id=123,
    image_id=456,
    embedding=image_vector
)

# Find similar images
similar = db.search_similar_images(
    query_embedding=new_image_vector,
    threshold=0.88  # 88% similar
)
# Returns: [{listing_id: 100, similarity: 0.92}, ...]
```

**Why ChromaDB:**
- Free and open source
- Persistent (data saved to disk)
- Fast similarity search (cosine distance)
- No server needed
- Easy to use

### 4. Duplicate Detection

**Multi-Modal Matching:**
```python
# Check both image AND text similarity
duplicates = db.find_duplicates(
    image_embedding=img_vector,
    text_embedding=text_vector
)

if duplicates['is_duplicate']:
    # Same apartment posted in 3 different channels
    print(f"Duplicate! Similar to listing {duplicates['matches'][0]['listing_id']}")
    print(f"Image similarity: {duplicates['matches'][0]['image_similarity']}")
    print(f"Text similarity: {duplicates['matches'][0]['text_similarity']}")
```

## Installation

### Step 1: Install Dependencies

```bash
cd crawler

# Install Python packages
pip install telethon pyyaml requests anthropic openai chromadb sentence-transformers tqdm Pillow

# Install PyTorch (choose based on your system)
# For CPU:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# For CUDA (if you have NVIDIA GPU):
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Install CLIP
pip install git+https://github.com/openai/CLIP.git
```

### Step 2: Configure LLM API Key

Edit `crawler/llm_config.py`:

```python
# Get API key from https://console.anthropic.com/
ANTHROPIC_API_KEY = 'sk-ant-your-key-here'

# Or set environment variable:
export ANTHROPIC_API_KEY='sk-ant-your-key-here'
```

### Step 3: Test Components

```bash
# Test LLM extraction
python llm_extractor.py

# Test CLIP image embeddings
python image_embeddings.py photo1.jpg photo2.jpg

# Test vector database
python vector_db.py

# Test configuration
python llm_config.py
```

## Configuration

### LLM Settings (`llm_config.py`)

```python
# Choose LLM provider
LLM_PROVIDER = 'anthropic'  # or 'openai' or 'ollama' (free, local)

# Cost optimization
USE_HAIKU_FOR_SIMPLE_SCHEMAS = True  # Use cheaper model for simple extractions
ENABLE_RESPONSE_CACHE = True  # Cache responses to save money

# Duplicate detection thresholds
IMAGE_SIMILARITY_THRESHOLD = 0.88  # Instagram uses ~0.85-0.90
TEXT_SIMILARITY_THRESHOLD = 0.92
```

### What to Adjust:

**Image Similarity Threshold (0.0 - 1.0):**
- `0.95+`: Only exact duplicates (same photo)
- `0.88`: Recommended - catches duplicates, few false positives
- `0.75`: Catches variations (different angles, lighting)
- `0.50`: Too loose - many false positives

**Text Similarity Threshold:**
- `0.95+`: Almost identical text
- `0.92`: Recommended - same content, minor differences
- `0.80`: Similar topic, different wording

## Usage Examples

### Example 1: Real Estate with Duplicates

**Channel A posts:**
```
3-xonali kvartira Chilonzorda
Narxi: 120.000$
80m², 5/9-qavat
Tel: +998901234567
[Photos: IMG_001.jpg, IMG_002.jpg]
```

**Channel B posts (same apartment):**
```
Продается 3-комнатная квартира
Чилонзор, 80кв.м, 5 этаж
Цена: $120,000 (торг)
Тел: +998901234567
[Photos: Different angle, but same apartment]
```

**What Happens:**

1. **Channel A Message:**
   - LLM extracts: `{rooms: 3, price: 120000, district: "Chilonzor", area_sqm: 80}`
   - CLIP generates embeddings for images
   - Stored in database

2. **Channel B Message:**
   - LLM extracts: `{rooms: 3, price: 120000, district: "Chilonzor", area_sqm: 80}`
   - CLIP generates embeddings
   - Vector search finds similar images: **Similarity: 0.89**
   - Text comparison: **Similarity: 0.94**
   - **Result: Flagged as duplicate!**

3. **Database Entry:**
```json
{
  "listing_id": 456,
  "duplicate_of": 123,
  "similarity_score": 0.91,
  "duplicate_type": "both"
}
```

### Example 2: Product Listings

**Different formats, same product:**

**Format 1 (Casual):**
```
iPhone 15 Pro yangi
12 million only!!
chilonzor +998901234567
```

**Format 2 (Formal):**
```
Продаю: Apple iPhone 15 Pro 256GB
Состояние: Новый, запечатанный
Цена: 12.000.000 сум
Район: Чилонзор
Контакт: +998 90 123 45 67
```

**LLM Extracts Both as:**
```json
{
  "title": "iPhone 15 Pro",
  "condition": "new",
  "price": 12000000,
  "location": "Chilonzor",
  "contact_phone": "+998901234567"
}
```

## Monitoring Duplicates

### API Endpoints

```bash
# Get statistics
curl http://localhost:5000/api/Crawler/statistics

# Response:
{
  "listings": {
    "unique": 850,
    "duplicates": 150,
    "total": 1000
  },
  "images": {
    "unique": 3200,
    "duplicates": 800
  }
}

# Get all duplicates
curl http://localhost:5000/api/Crawler/duplicates

# Get listings (excluding duplicates)
curl "http://localhost:5000/api/Crawler/listings?include_duplicates=false"
```

### Duplicate Handling Strategies

**Option 1: Skip Duplicates**
```python
DUPLICATE_ACTION = 'skip'  # Don't store duplicates
```

**Option 2: Flag Duplicates**
```python
DUPLICATE_ACTION = 'flag'  # Store but mark as duplicate
```

**Option 3: Merge Duplicates**
```python
DUPLICATE_ACTION = 'merge'  # Combine information from both
# E.g., keep both phone numbers, merge image galleries
```

## Cost Breakdown

### For 1000 Messages:

**LLM Extraction:**
- Simple schemas (≤5 fields): 500 messages × $0.0001 = **$0.05**
- Complex schemas (>5 fields): 500 messages × $0.003 = **$1.50**
- **Subtotal: ~$1.55**

**Image Processing:**
- CLIP embeddings: 3000 images × $0 = **$0** (runs locally)
- Vector storage: $0 (ChromaDB is free)

**Text Embeddings:**
- Sentence Transformers: 1000 texts × $0 = **$0** (runs locally)

**Total: ~$1.55 per 1000 messages**

**Compared to using Vision API:**
- GPT-4 Vision: 3000 images × $0.01 = **$30**
- Claude Vision: 3000 images × $0.008 = **$24**

**Savings: $22-28 per 1000 messages!**

## Performance

### Throughput:

| Component | Speed | Bottleneck |
|-----------|-------|------------|
| LLM Extraction | 2-5 sec/message | API rate limits |
| CLIP Embedding | 100ms/image (GPU) | GPU availability |
| CLIP Embedding | 500ms/image (CPU) | CPU speed |
| Vector Search | <10ms | Database size |

**Expected: ~10-20 messages/minute**

### Optimization Tips:

1. **Use GPU for CLIP** (5x faster)
2. **Batch images** (process multiple at once)
3. **Use Haiku for simple schemas** (10x cheaper, faster)
4. **Enable caching** (avoid re-processing identical messages)

## Troubleshooting

**"CUDA not available"**
- CLIP will use CPU (slower but works)
- Install CUDA toolkit for GPU support

**"Anthropic API rate limit"**
- Reduce batch size
- Add delays between requests
- Upgrade API tier

**"ChromaDB slow with millions of vectors"**
- Switch to FAISS (faster for large scale)
- Use `VECTOR_DB_TYPE = 'faiss'` in config

**"Too many duplicates detected"**
- Increase similarity threshold (try 0.92)
- Check if images are watermarked (throws off CLIP)

**"Missing duplicates"**
- Decrease threshold (try 0.82)
- Check if images are heavily edited

## Advanced Usage

### Custom Duplicate Logic

```python
# In vector_db.py
def is_duplicate_apartment(listing1, listing2):
    """Custom logic for real estate"""
    # Same district + similar price + similar area → likely duplicate
    if (listing1['district'] == listing2['district'] and
        abs(listing1['price'] - listing2['price']) / listing1['price'] < 0.05 and
        abs(listing1['area_sqm'] - listing2['area_sqm']) < 5):
        return True
    return False
```

### Multi-Stage Filtering

```python
# 1. Quick image similarity
if image_similarity > 0.95:
    return "exact_duplicate"

# 2. Check structured data
if same_phone_number and same_district:
    return "likely_duplicate"

# 3. Text similarity
if text_similarity > 0.90:
    return "possible_duplicate"

return "unique"
```

## Next Steps

1. ✅ Set up API keys
2. ✅ Test components individually
3. ✅ Configure similarity thresholds
4. ✅ Create custom schemas
5. ✅ Run the full crawler
6. ✅ Monitor duplicate detection
7. ✅ Optimize based on your use case

## Files Created

- `crawler/llm_config.py` - Configuration for LLM and embeddings
- `crawler/llm_extractor.py` - LLM-based extraction
- `crawler/image_embeddings.py` - CLIP image embeddings
- `crawler/vector_db.py` - ChromaDB vector database
- `api/server_llm.py` - API with embedding support
- `crawler/requirements.txt` - Updated dependencies

---

**This system combines the intelligence of LLMs with the cost-effectiveness of local embeddings** - giving you the best of both worlds!

**Questions? Issues? Check the logs in `llm_extraction.log` and `similarity_searches.log`**
