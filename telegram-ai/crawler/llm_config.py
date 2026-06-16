# LLM Configuration for Telegram Crawler
# Uses LLM for text extraction + CLIP for image embeddings (cost-effective!)

import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env from crawler directory (same directory as this file)
    env_path = Path(__file__).parent / '.env'
    load_dotenv(dotenv_path=env_path)
    print(f"[OK] Loaded environment variables from {env_path}")
except ImportError:
    print("[WARNING] python-dotenv not installed. Install with: pip install python-dotenv")
    print("   Environment variables will be loaded from system only.")
except Exception as e:
    print(f"[WARNING] Could not load .env file: {e}")

# ===========================
# LLM Provider Configuration
# ===========================

# Choose your LLM provider: 'anthropic', 'openai', 'gemini', 'ollama'
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'anthropic')

# API Keys (loaded from .env file)
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', 'your-anthropic-api-key-here')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'your-openai-api-key-here')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY', '')

# Model selection (loaded from .env file) - ONE MODEL ONLY
ANTHROPIC_MODEL = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-2024-08-06')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite')

# Ollama (local LLM via Docker - free, no rate limits)
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')


# ===========================
# Telegram Configuration
# ===========================

# Historical Messages Processing
PROCESS_HISTORICAL_MESSAGES = int(os.getenv('PROCESS_HISTORICAL_MESSAGES', '10'))

# ===========================
# Image Embedding Configuration
# ===========================

# Use CLIP for image embeddings (FREE, runs locally)
IMAGE_EMBEDDING_MODEL = 'clip'  # Always use CLIP - it's free and excellent

# CLIP model options:
# - 'ViT-B/32': Fast, 512-dim embeddings, good for most use cases
# - 'ViT-B/16': Better quality, 512-dim, slightly slower
# - 'ViT-L/14': Best quality, 768-dim, slower but more accurate
CLIP_MODEL_NAME = os.getenv('CLIP_MODEL_NAME', 'ViT-B/32')

# Device for CLIP
CLIP_DEVICE = os.getenv('CLIP_DEVICE', 'cuda')  # 'cuda' if you have GPU, 'cpu' otherwise

# ===========================
# Text Embedding Configuration
# ===========================

# For semantic text similarity (FREE, runs locally)
TEXT_EMBEDDING_MODEL = 'sentence-transformers'
SENTENCE_TRANSFORMER_MODEL = 'paraphrase-multilingual-mpnet-base-v2'  # Supports Uzbek, Russian, English

# Alternative: all-MiniLM-L6-v2 (faster but English only)

# ===========================
# Vector Database Configuration
# ===========================

# Choose vector database: 'sqlite-vss', 'chromadb', 'faiss'
VECTOR_DB_TYPE = os.getenv('VECTOR_DB_TYPE', 'chromadb')  # Recommended: Easy to use, persistent, free

# ChromaDB settings (recommended)
CHROMA_PERSIST_DIR = os.getenv('CHROMA_PERSIST_DIR', './vector_db')
CHROMA_IMAGE_COLLECTION = 'image_embeddings'
CHROMA_TEXT_COLLECTION = 'text_embeddings'

# FAISS settings (alternative - very fast, good for millions of images)
FAISS_INDEX_PATH = './faiss_index'
FAISS_INDEX_TYPE = 'IVFFlat'  # or 'Flat' for exact search

# SQLite-VSS settings (alternative - stores in SQLite)
SQLITE_VSS_PATH = './embeddings.db'

# ===========================
# Similarity Thresholds
# ===========================

# Image similarity (0.0 to 1.0)
# Instagram uses ~0.85-0.90 for duplicate detection
IMAGE_SIMILARITY_THRESHOLD = float(os.getenv('IMAGE_SIMILARITY_THRESHOLD', '0.88'))  # Images above this are likely duplicates
IMAGE_NEAR_DUPLICATE_THRESHOLD = 0.75  # Similar images (same property, different angle)

# Text similarity (0.0 to 1.0)
TEXT_SIMILARITY_THRESHOLD = float(os.getenv('TEXT_SIMILARITY_THRESHOLD', '0.92'))  # Very similar text (likely duplicate listing)

# Combined duplicate detection (image + text)
REQUIRE_BOTH_SIMILAR = False  # If True, both image AND text must be similar
DUPLICATE_SCORE_THRESHOLD = 0.85  # Weighted average of image + text similarity

# ===========================
# LLM Extraction Settings
# ===========================

# Temperature (0.0 = deterministic, 1.0 = creative)
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.0'))  # Use 0 for consistent structured extraction

# Max tokens for extraction response
MAX_TOKENS = int(os.getenv('MAX_TOKENS', '2000'))

# Retry settings
MAX_LLM_RETRIES = 3
LLM_RETRY_DELAY = 2  # seconds

# Timeout
LLM_TIMEOUT_SECONDS = 60

# ===========================
# Cost Optimization
# ===========================

# Cache LLM responses (saves money on identical messages)
ENABLE_RESPONSE_CACHE = os.getenv('ENABLE_RESPONSE_CACHE', 'true').lower() == 'true'
CACHE_DIR = './llm_cache'
CACHE_TTL_HOURS = 168  # 1 week

# Skip LLM for obviously invalid messages
ENABLE_PREFILTERING = True
MIN_TEXT_LENGTH = 10  # Skip very short messages
MAX_TEXT_LENGTH = 10000  # Skip very long messages (likely spam)

# Batch processing
BATCH_SIZE = 10  # Process N messages before writing to DB
BATCH_TIMEOUT_SECONDS = 60

# ===========================
# Image Processing Settings
# ===========================

# Resize images before embedding (saves memory)
RESIZE_IMAGES = True
MAX_IMAGE_SIZE = (512, 512)  # Resize to this max dimension

# Image quality threshold
MIN_IMAGE_SIZE = (100, 100)  # Skip tiny images
MIN_IMAGE_FILE_SIZE_KB = 10  # Skip very small files (likely icons)

# Process N images in parallel
IMAGE_BATCH_SIZE = 4

# ===========================
# Duplicate Detection Strategy
# ===========================

# When duplicate is found, what to do?
DUPLICATE_ACTION = os.getenv('DUPLICATE_ACTION', 'skip')  # 'skip', 'merge', 'flag', 'store_both'

# If 'merge', which fields to keep from original vs new
MERGE_STRATEGY = 'keep_first'  # 'keep_first', 'keep_latest', 'merge_all'

# Store similarity scores with listings
STORE_SIMILARITY_SCORES = True

# ===========================
# Logging & Debugging
# ===========================

# Log LLM requests/responses
LOG_LLM_CALLS = os.getenv('LOG_LLM_CALLS', 'true').lower() == 'true'
LLM_LOG_FILE = 'llm_extraction.log'

# Log similarity searches
LOG_SIMILARITY_SEARCHES = os.getenv('LOG_SIMILARITY_SEARCHES', 'true').lower() == 'true'
SIMILARITY_LOG_FILE = 'similarity_searches.log'

# Save failed extractions for review
SAVE_FAILED_EXTRACTIONS = os.getenv('SAVE_FAILED_EXTRACTIONS', 'true').lower() == 'true'
FAILED_EXTRACTIONS_DIR = 'failed_extractions'

# Verbose mode
VERBOSE = os.getenv('VERBOSE', 'true').lower() == 'true'

# ===========================
# Performance Settings
# ===========================

# Number of similar images to retrieve
TOP_K_SIMILAR_IMAGES = 5

# Number of similar texts to retrieve
TOP_K_SIMILAR_TEXTS = 3

# Parallel processing
MAX_WORKERS = 4  # Number of parallel threads for image embedding

# Memory limits
MAX_CACHE_SIZE_MB = 500  # Maximum cache size in memory

# ===========================
# Validation
# ===========================

def validate_config():
    """Validate configuration before running"""
    errors = []
    warnings = []

    # Check LLM configuration
    if LLM_PROVIDER == 'anthropic' and ANTHROPIC_API_KEY == 'your-anthropic-api-key-here':
        errors.append("[ERROR] ANTHROPIC_API_KEY not set. Get it from https://console.anthropic.com/")

    if LLM_PROVIDER == 'openai' and OPENAI_API_KEY == 'your-openai-api-key-here':
        errors.append("[ERROR] OPENAI_API_KEY not set. Get it from https://platform.openai.com/")

    if LLM_PROVIDER == 'gemini' and not GEMINI_API_KEY:
        errors.append("[ERROR] GEMINI_API_KEY not set. Get it from https://aistudio.google.com/app/apikey")

    if LLM_PROVIDER == 'ollama':
        try:
            import urllib.request
            urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        except Exception:
            errors.append(f"[ERROR] Ollama not reachable at {OLLAMA_BASE_URL}. Start with: docker start ollama")

    # Check if CUDA is available for CLIP
    if CLIP_DEVICE == 'cuda':
        try:
            import torch
            if not torch.cuda.is_available():
                warnings.append("[WARNING] CUDA not available. CLIP will use CPU (slower)")
        except ImportError:
            warnings.append("[WARNING] PyTorch not installed. Install with: pip install torch")

    # Check vector DB
    if VECTOR_DB_TYPE == 'chromadb':
        try:
            import chromadb
        except ImportError:
            errors.append("[ERROR] ChromaDB not installed. Install with: pip install chromadb")

    return errors, warnings

def print_config_summary():
    """Print configuration summary"""
    print("\n" + "="*60)
    print("Telegram Crawler Configuration")
    print("="*60)
    print(f"LLM Provider: {LLM_PROVIDER}")
    if LLM_PROVIDER == 'anthropic':
        print(f"  Model: {ANTHROPIC_MODEL}")
    elif LLM_PROVIDER == 'openai':
        print(f"  Model: {OPENAI_MODEL}")
    elif LLM_PROVIDER == 'gemini':
        print(f"  Model: {GEMINI_MODEL}")
    elif LLM_PROVIDER == 'ollama':
        print(f"  Model: {OLLAMA_MODEL}")
        print(f"  Base URL: {OLLAMA_BASE_URL}")

    print(f"\nImage Embeddings: CLIP {CLIP_MODEL_NAME} (FREE, local)")
    print(f"  Device: {CLIP_DEVICE}")
    print(f"  Similarity threshold: {IMAGE_SIMILARITY_THRESHOLD}")

    print(f"\nText Embeddings: {SENTENCE_TRANSFORMER_MODEL} (FREE, local)")
    print(f"  Similarity threshold: {TEXT_SIMILARITY_THRESHOLD}")

    print(f"\nVector Database: {VECTOR_DB_TYPE}")
    if VECTOR_DB_TYPE == 'chromadb':
        print(f"  Location: {CHROMA_PERSIST_DIR}")

    print(f"\nDuplicate Detection:")
    print(f"  Action: {DUPLICATE_ACTION}")
    print(f"  Image threshold: {IMAGE_SIMILARITY_THRESHOLD}")
    print(f"  Text threshold: {TEXT_SIMILARITY_THRESHOLD}")

    print(f"\nCost Optimization:")
    print(f"  Response cache: {'Enabled' if ENABLE_RESPONSE_CACHE else 'Disabled'}")
    print(f"  Prefiltering: {'Enabled' if ENABLE_PREFILTERING else 'Disabled'}")
    print("="*60 + "\n")

if __name__ == '__main__':
    errors, warnings = validate_config()

    if errors:
        print("\n[ERROR] Configuration Errors:")
        for error in errors:
            print(f"  {error}")
        print("\n")

    if warnings:
        print("\n[WARNING] Warnings:")
        for warning in warnings:
            print(f"  {warning}")
        print("\n")

    if not errors:
        print("[OK] Configuration valid!")
        print_config_summary()

        print("\nCost Estimate:")
        if ANTHROPIC_MODEL == 'claude-3-5-sonnet-20241022':
            print("  - LLM (text extraction): ~$0.003 per message (Sonnet)")
            print("  - Estimated: ~$3 per 1000 messages")
        elif ANTHROPIC_MODEL == 'claude-3-5-haiku-20241022':
            print("  - LLM (text extraction): ~$0.00025 per message (Haiku)")
            print("  - Estimated: ~$0.25 per 1000 messages")
        print("  - Image embeddings: FREE (CLIP runs locally)")
        print("  - Text embeddings: FREE (Sentence Transformers)")
        print("  - Vector search: FREE (ChromaDB)")
