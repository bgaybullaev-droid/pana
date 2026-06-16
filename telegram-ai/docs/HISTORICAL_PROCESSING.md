# Historical Message Processing

## Overview

The crawler can now process **past messages** when it starts, giving you immediate results to see. This is perfect for testing and getting instant feedback.

## Configuration

Edit `crawler/.env`:

```env
# Historical Messages Processing
# How many past messages to process on startup (per channel)
# Set to 0 to only monitor new messages
# Recommended: 10-50 for initial testing, then set to 0 for production
PROCESS_HISTORICAL_MESSAGES=10
```

### Configuration Options

| Value | Behavior | Use Case |
|-------|----------|----------|
| `0` | Only monitor new messages | **Production mode** - only process new posts |
| `10` | Process last 10 messages per channel | **Testing** - see immediate results (recommended) |
| `50` | Process last 50 messages per channel | **Initial import** - populate database with recent data |
| `100` | Process last 100 messages per channel | **Full import** - comprehensive historical data |
| `500+` | Process many messages | **Bulk import** - may take hours, use with caution |

## How It Works

### Startup Sequence

1. **Connect to Telegram**: Authenticate with your account
2. **Process Historical Messages**:
   - Iterate through all configured channels
   - Fetch last N messages from each channel (N = `PROCESS_HISTORICAL_MESSAGES`)
   - Extract data using LLM
   - Check for duplicates
   - Save to database
   - Show progress and stats
3. **Switch to Real-Time Mode**: Start monitoring for new messages
4. **Continue Running**: Process new messages as they arrive

### Example Output

```
============================================================
Processing 10 historical messages per channel...
============================================================

Found 14 channels to process

Processing @baburieltor...
Retrieved 10 messages from @baburieltor
[HISTORICAL] Extracting from @baburieltor message 12345...
Extracted: 3-xonali kvartira, Chilonzor, 120 mln sum...
Created listing #1
Uploaded image #1
[HISTORICAL] Extracting from @baburieltor message 12346...
...

Processing @realtor_alii...
Retrieved 10 messages from @realtor_alii
[HISTORICAL] Extracting from @realtor_alii message 54321...
...

============================================================
Historical Processing Complete!
============================================================
Total processed: 140
Success: 87
Failed: 53
============================================================

============================================================
Switching to REAL-TIME monitoring mode...
============================================================

Now listening for new messages...
Press Ctrl+C to stop

[REALTIME] Extracting from @baburieltor message 12400...
Extracted: Yangi uy, Sergeli, $45,000...
Created listing #88
Uploaded image #88

Real-time Stats: Processed=1, Success=1, Failed=0
```

## Usage

### Windows

```bash
cd crawler
start_crawler_with_history.bat
```

### Linux/Mac

```bash
cd crawler
chmod +x start_crawler_with_history.sh
./start_crawler_with_history.sh
```

### Manual

```bash
cd crawler
source venv/bin/activate  # or: call venv\Scripts\activate.bat
python FlexibleCrawlerWithHistory.py
```

## Performance Estimates

Based on 14 real estate channels:

| Setting | Messages Processed | Time Required | Success Rate |
|---------|-------------------|---------------|--------------|
| `PROCESS_HISTORICAL_MESSAGES=10` | 140 messages | ~5-10 minutes | ~60-70% (some have no photos) |
| `PROCESS_HISTORICAL_MESSAGES=50` | 700 messages | ~30-60 minutes | ~60-70% |
| `PROCESS_HISTORICAL_MESSAGES=100` | 1400 messages | ~1-2 hours | ~60-70% |

**Note**: Not all messages will be processed successfully because:
- Some messages have no photos (skipped)
- Some messages are too short (skipped)
- Some messages are text-only announcements (skipped)
- Only real property listings with photos are extracted

## Why Some Messages Fail

The crawler filters messages based on:

1. **Must have photo**: Real estate listings require images
2. **Must have text**: Need description for extraction
3. **Minimum text length**: At least 10 characters
4. **Valid schema**: Channel must have associated schema

Example filtered messages:
- "Кто хочет купить квартиру?" (no photo, question)
- Empty forwarded messages
- Service messages
- Very short messages

## Recommended Workflow

### First Time Setup (Testing)

1. **Set high value to see results**:
   ```env
   PROCESS_HISTORICAL_MESSAGES=10
   ```

2. **Start crawler**:
   ```bash
   cd crawler
   start_crawler_with_history.bat
   ```

3. **Watch the output**: You should see listings being extracted immediately

4. **Check API/database**: Verify data is being saved
   ```bash
   curl http://localhost:5000/api/Crawler/statistics
   ```

### Production Mode

Once you're satisfied with testing:

1. **Disable historical processing**:
   ```env
   PROCESS_HISTORICAL_MESSAGES=0
   ```

2. **Restart crawler**: Now only processes new messages

3. **Lower resource usage**: No startup delay, only real-time processing

## Comparison

### Old Crawler (No Historical Processing)

```
Starting crawler...
Now listening for new messages...
[Waiting for new messages...]
[Could wait hours if channels are quiet]
```

**Problem**: No immediate feedback, have to wait for new posts

### New Crawler (With Historical Processing)

```
Starting crawler...
Processing 10 historical messages per channel...
[HISTORICAL] Extracting from @baburieltor message 12345...
Created listing #1
[HISTORICAL] Extracting from @baburieltor message 12346...
Created listing #2
...
Historical Processing Complete!
Total processed: 140, Success: 87

Switching to REAL-TIME monitoring mode...
Now listening for new messages...
```

**Benefit**: Immediate results, database populated, can see system working

## Cost Impact

Historical processing uses the same LLM as real-time:

- **10 messages × 14 channels = 140 messages**
  - At ~60% success rate = ~84 LLM calls
  - Cost with Sonnet: 84 × $0.003 = **$0.25**
  - Cost with Haiku: 84 × $0.00025 = **$0.02**

- **50 messages × 14 channels = 700 messages**
  - At ~60% success rate = ~420 LLM calls
  - Cost with Sonnet: 420 × $0.003 = **$1.26**
  - Cost with Haiku: 420 × $0.00025 = **$0.11**

**Recommendation**: Use historical processing for testing, then disable for production to save costs.

## Troubleshooting

### No Messages Processed

```
Retrieved 10 messages from @baburieltor
(no extraction output)
```

**Possible causes**:
- Channel has no photos in recent messages
- Messages are too short
- All messages are text-only announcements

**Solution**: Increase `PROCESS_HISTORICAL_MESSAGES` to 50 or 100

### Rate Limiting

```
Error processing message: FloodWaitError: A wait of 60 seconds is required
```

**Solution**: The crawler automatically waits 1 second between messages. If you still hit rate limits, the error message will tell you how long to wait.

### Memory Issues

```
MemoryError: Unable to allocate array
```

**Solution**: Reduce `PROCESS_HISTORICAL_MESSAGES` or restart Python with more memory

## Files Modified

| File | Purpose |
|------|---------|
| `crawler/.env` | Added `PROCESS_HISTORICAL_MESSAGES=10` |
| `crawler/.env.example` | Added configuration example |
| `crawler/llm_config.py` | Added `PROCESS_HISTORICAL_MESSAGES` variable |
| `crawler/FlexibleCrawlerWithHistory.py` | New crawler with historical processing |
| `crawler/start_crawler_with_history.bat` | Windows launcher |
| `crawler/start_crawler_with_history.sh` | Linux/Mac launcher |

## Summary

✅ **Problem solved**: No more waiting for new messages to test the system
✅ **Immediate results**: See 10-100 listings extracted on startup
✅ **Configurable**: Set to 0 for production, 10-50 for testing
✅ **Seamless**: Automatically switches to real-time mode after historical processing
✅ **Same quality**: Uses same LLM extraction for both historical and real-time messages

**Recommended setting for testing**: `PROCESS_HISTORICAL_MESSAGES=10`
**Recommended setting for production**: `PROCESS_HISTORICAL_MESSAGES=0`
