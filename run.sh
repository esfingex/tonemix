#!/bin/bash
# ToneMix - Run Script

set -e

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Run ./setup.sh first"
    exit 1
fi

# Run the application
echo "🎵 Starting ToneMix Pro..."
python main.py
