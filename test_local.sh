#!/bin/bash
# Local testing script for YouTube Analyzer

set -e

echo "🧪 YouTube Analyzer - Local Testing Script"
echo "=========================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Install test dependencies
echo "📥 Installing test dependencies..."
pip install requests

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
API_KEY=dev_api_key_123
GEMINI_API_KEY=your_gemini_api_key_here
USE_GCS_STORAGE=false
EOF
    echo "⚠️  Please edit .env file and add your Gemini API key"
    echo "   You can get one from: https://makersuite.google.com/app/apikey"
    read -p "Press Enter after updating the .env file..."
fi

# Load environment variables
export $(cat .env | xargs)

# Check if Gemini API key is set
if [ "$GEMINI_API_KEY" = "your_gemini_api_key_here" ]; then
    echo "❌ Please set your Gemini API key in the .env file"
    exit 1
fi

# Start the application in background
echo "🚀 Starting the application..."
python3 fastapi_youtube_analyzer_local_storage.py &
APP_PID=$!

# Wait for application to start
echo "⏳ Waiting for application to start..."
sleep 5

# Test the application
echo "🧪 Running tests..."
python3 test_api.py

# Stop the application
echo "🛑 Stopping the application..."
kill $APP_PID

echo "✅ Local testing completed!"
