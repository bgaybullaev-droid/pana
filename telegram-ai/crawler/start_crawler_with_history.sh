#!/bin/bash
# Start Flexible Crawler with Historical Message Processing

cd "$(dirname "$0")"

echo "============================================================"
echo "Telegram Crawler - With Historical Processing"
echo "============================================================"
echo ""

# Check if venv exists
if [ ! -f "venv/bin/activate" ]; then
    echo "[ERROR] Virtual environment not found!"
    echo "Please run setup.sh first"
    exit 1
fi

# Activate venv
source venv/bin/activate

echo "[INFO] Starting crawler with historical message processing..."
echo "[INFO] Edit .env to configure PROCESS_HISTORICAL_MESSAGES"
echo ""

# Run crawler
python FlexibleCrawlerWithHistory.py
