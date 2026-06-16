#!/bin/bash
# Auto-join all configured Telegram channels

cd "$(dirname "$0")"

echo "============================================================"
echo "Telegram Channel Auto-Join Script"
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

# Run join script
python join_channels.py
