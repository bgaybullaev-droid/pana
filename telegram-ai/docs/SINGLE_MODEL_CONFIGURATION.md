# Single Model Configuration

## Overview

The system has been simplified to use **ONE model only** instead of dual-model auto-selection (Haiku for simple schemas + Sonnet for complex schemas).

## What Changed

### 1. Configuration Files

**crawler/.env and .env.example:**
- ✅ Removed `ANTHROPIC_HAIKU_MODEL` variable
- ✅ Removed `USE_HAIKU_FOR_SIMPLE_SCHEMAS` flag
- ✅ Added inline comments showing model options:
  ```env
  # Anthropic Model Selection (only one model used)
  # Options:
  #   claude-3-5-sonnet-20241022 (best quality, ~$3 per 1000 messages)
  #   claude-3-5-haiku-20241022 (cheaper, ~$0.25 per 1000 messages)
  ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
  ```

### 2. Code Changes

**crawler/llm_config.py:**
- Line 32-33: Removed `ANTHROPIC_HAIKU_MODEL` import from .env
- Line 107-108: Removed `USE_HAIKU_FOR_SIMPLE_SCHEMAS` and `SIMPLE_SCHEMA_MAX_FIELDS` variables
- Line 126-129: Removed duplicate `ENABLE_PREFILTERING` block
- Line 240-246: Simplified `print_config_summary()` to show only one model
- Line 265-267: Removed Haiku mention from cost optimization summary
- Line 288-297: Updated cost estimate logic to check single model type

**crawler/llm_extractor.py:**
- Line 16-28: Removed `ANTHROPIC_HAIKU_MODEL`, `USE_HAIKU_FOR_SIMPLE_SCHEMAS`, `SIMPLE_SCHEMA_MAX_FIELDS` from imports
- Line 130: Changed `extract_with_anthropic(prompt, use_haiku=False)` → `extract_with_anthropic(prompt)` (removed parameter)
- Line 133: Changed `model = ANTHROPIC_HAIKU_MODEL if use_haiku else ANTHROPIC_MODEL` → `model = ANTHROPIC_MODEL`
- Line 214-221: Removed auto-selection logic that counted fields and decided which model to use
- Line 221: Changed `self.extract_with_anthropic(prompt, use_haiku=use_haiku)` → `self.extract_with_anthropic(prompt)`

### 3. Unicode Fixes for Windows

**crawler/llm_config.py:**
- Replaced all Unicode symbols (✓, ✅, ❌, ⚠️, 📋, 💰) with `[OK]`, `[ERROR]`, `[WARNING]` text tags
- This fixes `UnicodeEncodeError: 'charmap' codec can't encode character` on Windows console (cp1251 encoding)

## How to Use

### Quick Start

1. **Choose your model** by editing `crawler/.env`:
   ```env
   # For best quality (recommended):
   ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

   # For lower cost:
   ANTHROPIC_MODEL=claude-3-5-haiku-20241022
   ```

2. **Set your API key** in `crawler/.env`:
   ```env
   ANTHROPIC_API_KEY=sk-ant-api03-YOUR-ACTUAL-KEY-HERE
   ```

3. **Test configuration**:
   ```bash
   cd crawler
   python llm_config.py
   ```

   Expected output:
   ```
   [OK] Loaded environment variables from D:\...\crawler\.env
   [OK] Configuration valid!

   ============================================================
   Telegram Crawler Configuration
   ============================================================
   LLM Provider: anthropic
     Model: claude-3-5-sonnet-20241022

   Cost Estimate:
     - LLM (text extraction): ~$0.003 per message (Sonnet)
     - Estimated: ~$3 per 1000 messages
     - Image embeddings: FREE (CLIP runs locally)
     - Text embeddings: FREE (Sentence Transformers)
     - Vector search: FREE (ChromaDB)
   ```

## Cost Comparison

### Old System (Dual-Model Auto-Selection)
- **Simple schemas (≤5 fields)**: Haiku at $0.00025/message
- **Complex schemas (>5 fields)**: Sonnet at $0.003/message
- **Mixed workload (50/50)**: ~$1.50 per 1000 messages
- **Complexity**: Auto-selection logic, field counting, fallback handling

### New System (Single Model)
- **Sonnet-only**: $3 per 1000 messages (best quality)
- **Haiku-only**: $0.25 per 1000 messages (good quality, 12x cheaper)
- **Simplicity**: One model for everything, consistent extraction quality

## Model Selection Guide

### Use Sonnet (claude-3-5-sonnet-20241022) when:
- ✅ You need best extraction quality
- ✅ Handling complex multilingual text (Uzbek/Russian/English mix)
- ✅ Extracting from unstructured/inconsistent formats
- ✅ Cost is not a primary concern (~$3/1000 msgs)

### Use Haiku (claude-3-5-haiku-20241022) when:
- ✅ You need to minimize costs (12x cheaper)
- ✅ Working with simpler, structured text
- ✅ High message volume (tens of thousands/day)
- ✅ Acceptable to have slightly lower extraction accuracy

## Benefits of Single-Model Approach

1. **Simplicity**: No complex auto-selection logic to debug
2. **Predictability**: Same model for all extractions = consistent behavior
3. **Easier to understand**: One configuration variable, clear cost model
4. **Easier to debug**: All extractions use same model, easier to trace issues
5. **User control**: Explicit choice rather than automatic optimization

## Migration Notes

If you were using the old dual-model system:
- Your existing `.env` file will continue to work
- The `ANTHROPIC_HAIKU_MODEL` variable is now ignored
- The `USE_HAIKU_FOR_SIMPLE_SCHEMAS` variable is now ignored
- All extractions will use the model specified in `ANTHROPIC_MODEL`

## Files Modified

1. `crawler/.env` (90 lines) - Simplified model config
2. `crawler/.env.example` (90 lines) - Updated template
3. `crawler/llm_config.py` (297 lines) - Removed dual-model logic, fixed Unicode
4. `crawler/llm_extractor.py` (360 lines) - Removed `use_haiku` parameter

## Testing

Run the test suite to verify everything works:

```bash
cd crawler
python llm_config.py     # Should show [OK] Configuration valid!
python llm_extractor.py  # Should extract test message successfully
```

## Questions?

- For setup help: See `GETTING_STARTED.md` in root
- For API keys: See `ENV_SETUP_GUIDE.md`
- For full LLM guide: See `LLM_CRAWLER_GUIDE.md`
