#!/bin/bash
# Docker testing script for YouTube Analyzer

set -e

echo "🐳 YouTube Analyzer - Docker Testing Script"
echo "=========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is required but not installed."
    exit 1
fi

# Check if .env file exists for Docker
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file for Docker..."
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

# Stop any running containers
echo "🛑 Stopping any running containers..."
docker-compose down 2>/dev/null || true

# Build and start the application
echo "🚀 Building and starting the application..."
docker-compose up --build -d

# Wait for application to start
echo "⏳ Waiting for application to start..."
sleep 10

# Check if application is running
echo "🔍 Checking application health..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        echo "✅ Application is running!"
        break
    fi
    echo "⏳ Waiting for application to be ready... (attempt $i/30)"
    sleep 2
done

# Test the application
echo "🧪 Running tests..."
export API_BASE_URL=http://localhost:8000
export API_KEY=dev_api_key_123
python3 test_api.py

# Stop the containers
echo "🛑 Stopping containers..."
docker-compose down

echo "✅ Docker testing completed!"
