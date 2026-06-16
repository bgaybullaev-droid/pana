# Environment Setup Guide

## Quick Setup (3 Steps)

### 1. Copy the Example File

```bash
# The .env file is already created for you in the crawler/ directory!
# Just edit it with your actual values
```

### 2. Edit `.env` File

Open `crawler/.env` and fill in your values:

```bash
# Minimum required configuration:

# 1. Anthropic API Key (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here

# 2. Telegram Credentials (REQUIRED)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_PHONE_NUMBER=+998901234567
```

### 3. Install python-dotenv

```bash
pip install python-dotenv
```

That's it! The system will automatically load your `.env` file.

## Where to Get API Keys

### Anthropic (Claude) API Key

1. Go to: https://console.anthropic.com/
2. Sign up (free $5 credit)
3. Navigate to "API Keys"
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-`)
6. Paste into `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxx
   ```

### Telegram API Credentials

1. Go to: https://my.telegram.org/apps
2. Log in with your phone number
3. Click "API Development Tools"
4. Fill in the form (app title, short name)
5. You'll get:
   - `api_id` (a number)
   - `api_hash` (a string)
6. Paste into `.env`:
   ```
   TELEGRAM_API_ID=12345678
   TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
   TELEGRAM_PHONE_NUMBER=+998901234567
   ```

## All Available Settings

The `.env` file contains all configurable options:

```bash
# LLM Settings
ANTHROPIC_API_KEY=your-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
LLM_PROVIDER=anthropic

# Telegram Settings
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_hash
TELEGRAM_PHONE_NUMBER=+998901234567

# Image Processing
CLIP_MODEL_NAME=ViT-B/32
CLIP_DEVICE=cuda  # or 'cpu'

# Similarity Thresholds
IMAGE_SIMILARITY_THRESHOLD=0.88
TEXT_SIMILARITY_THRESHOLD=0.92

# Cost Optimization
USE_HAIKU_FOR_SIMPLE_SCHEMAS=true
ENABLE_RESPONSE_CACHE=true

# Duplicate Handling
DUPLICATE_ACTION=skip  # or 'flag', 'merge'

# Logging
VERBOSE=true
LOG_LLM_CALLS=true
```

## Testing Your Configuration

After setting up `.env`, test it:

```bash
cd crawler
python llm_config.py
```

You should see:
```
✓ Loaded environment variables from D:\...\telegram-ai\.env
✅ Configuration valid!
LLM Provider: anthropic
  Model: claude-3-5-sonnet-20241022
```

## Security Best Practices

### ⚠️ IMPORTANT: Keep `.env` Private!

1. **Never commit `.env` to git** - It's already in `.gitignore`
2. **Don't share your API keys** - They cost you money!
3. **Use `.env.example`** - For sharing configuration templates

### What's Safe to Share?

✅ Safe (share these):
- `.env.example` (template with fake values)
- Configuration files without keys
- Code files

❌ Never share:
- `.env` (contains real API keys)
- `.session` files (Telegram authentication)
- `*.db` files (your data)

## Alternative: Environment Variables

Instead of `.env` file, you can set environment variables directly:

**Windows (Command Prompt):**
```cmd
set ANTHROPIC_API_KEY=sk-ant-your-key-here
set TELEGRAM_API_ID=12345678
```

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-your-key-here"
$env:TELEGRAM_API_ID="12345678"
```

**Linux/Mac:**
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
export TELEGRAM_API_ID=12345678
```

**Make permanent (Linux/Mac):**

Add to `~/.bashrc` or `~/.zshrc`:
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
export TELEGRAM_API_ID=12345678
```

Then run:
```bash
source ~/.bashrc  # or ~/.zshrc
```

## Troubleshooting

### "Could not load .env file"

**Cause:** `python-dotenv` not installed

**Solution:**
```bash
pip install python-dotenv
```

### "API key not set"

**Cause:** `.env` file not found or API key missing

**Solution:**
1. Make sure `.env` exists in project root
2. Check the key is set: `ANTHROPIC_API_KEY=sk-ant-...`
3. No quotes needed around the value

### "Environment variables not loading"

**Check:**
1. File is named `.env` (not `env.txt` or `.env.txt`)
2. File is in project root (same level as `setup.bat`)
3. No extra spaces: `KEY=value` not `KEY = value`

### "Configuration shows default values"

The system will use defaults if `.env` values are missing. Example:

```python
# If .env has: CLIP_DEVICE=cpu
# Then CLIP_DEVICE = 'cpu'

# If .env missing CLIP_DEVICE
# Then CLIP_DEVICE = 'cuda' (default)
```

## File Structure

```
telegram-ai/
├── crawler/
│   ├── .env               # ← Your actual API keys (NEVER commit!)
│   ├── .env.example       # ← Template (safe to commit)
│   ├── setup.bat/.sh      # ← Setup scripts
│   └── llm_config.py      # ← Loads from .env
├── .gitignore             # ← Protects .env from git
└── ...
```

## What Gets Loaded?

When you run the crawler, it will:

1. Look for `.env` in crawler/ directory
2. Load all variables into environment
3. `llm_config.py` reads from environment
4. Uses defaults if variable not set

**Example:**
```
crawler/.env file:
  ANTHROPIC_API_KEY=sk-ant-abc123

llm_config.py:
  ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', 'default')
  # Result: 'sk-ant-abc123'
```

## Example `.env` File

```bash
# Minimum configuration to get started

ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_hash_here
TELEGRAM_PHONE_NUMBER=+998901234567

CLIP_DEVICE=cuda
IMAGE_SIMILARITY_THRESHOLD=0.88
```

Save this to `.env` and you're ready to go! 🚀

## Next Steps

After setting up `.env`:

1. ✅ Run `python llm_config.py` to test
2. ✅ Add channels to `crawler/schemas/*.yaml`
3. ✅ Run `start_api.bat` to start API server
4. ✅ Run `start_crawler.bat` to start crawler

---

**Questions?** Check `QUICK_START_LLM.md` for complete setup guide.
