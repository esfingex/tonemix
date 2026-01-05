#!/bin/bash
# ToneMix - Test Script

set -e

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Run ./setup.sh first"
    exit 1
fi

# Run tests
echo "🧪 Running ToneMix tests..."
pytest tests/ -v --color=yes
