#!/bin/bash
# Telegram AI System Startup Script
# This script starts the API server and provides instructions for the bot

echo "============================================================"
echo "TELEGRAM AI SYSTEM - STARTUP"
echo "============================================================"
echo ""

echo "[1/2] Starting API Server (SQLite)..."
cd api
python server_sqlite.py &
API_PID=$!

sleep 3

echo "[2/2] API Server started successfully!"
echo ""
echo "============================================================"
echo "SYSTEM STATUS"
echo "============================================================"
echo " API Server: http://localhost:5000"
echo " Health Check: http://localhost:5000/health"
echo " Database: SQLite (telegram_listings.db)"
echo " Uploads: uploads/ directory"
echo " Process ID: $API_PID"
echo "============================================================"
echo ""
echo "Next Steps:"
echo " 1. Test the system: python test_system.py"
echo " 2. Configure Telegram credentials in crawler/config.py"
echo " 3. Run the bot: cd crawler && python Crawler.py"
echo ""
echo "To stop: kill $API_PID or press Ctrl+C"
echo ""
echo "Documentation: See SETUP.md for complete instructions"
echo "============================================================"

# Keep script running
wait $API_PID
