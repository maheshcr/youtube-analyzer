# YouTube Video Content Analyzer

A FastAPI-based service that analyzes YouTube videos using Google's Gemini AI to extract content insights, topics, and interest categorization.

## Features

- 🎥 **YouTube Video Analysis**: Downloads and analyzes YouTube videos using yt-dlp
- 🤖 **AI-Powered Insights**: Uses Google Gemini AI for content analysis
- 📊 **Structured Results**: Returns topic, summary, and interest categorization
- 🔄 **Background Processing**: Asynchronous task processing with status tracking
- ☁️ **Cloud Storage Support**: Optional Google Cloud Storage integration
- 🔐 **API Key Authentication**: Secure API access
- 🐳 **Docker Ready**: Containerized deployment
- 📈 **Health Monitoring**: Built-in health checks and monitoring

## Architecture

The application consists of two main versions:

1. **`fastapi_youtube_analyzer.py`** - Production version with Google Cloud Storage support
2. **`fastapi_youtube_analyzer_local_storage.py`** - Local development version

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/health` | GET | Detailed health status |
| `/analyze-video/` | POST | Start video analysis |
| `/task-status/{task_id}` | GET | Get task status and results |
| `/tasks` | GET | List all tasks |
| `/task/{task_id}` | DELETE | Delete completed task |

## Quick Start

### Prerequisites

- Python 3.11+
- Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
- Docker (optional)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd youtube-analyzer
   ```

2. **Set up environment**
   ```bash
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   # Create .env file
   cat > .env << EOF
   API_KEY=your_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   USE_GCS_STORAGE=false
   EOF
   ```

4. **Run the application**
   ```bash
   # For local development
   python3 fastapi_youtube_analyzer_local_storage.py
   
   # Or for production features
   python3 fastapi_youtube_analyzer.py
   ```

5. **Test the application**
   ```bash
   # Make test scripts executable
   chmod +x test_local.sh test_docker.sh
   
   # Run local tests
   ./test_local.sh
   
   # Or run Docker tests
   ./test_docker.sh
   ```

### Docker Deployment

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

2. **Or build and run manually**
   ```bash
   docker build -t youtube-analyzer .
   docker run -p 8123:8123 --env-file .env youtube-analyzer
   ```

## Testing

### Automated Testing

Run the comprehensive test suite:

```bash
# Test with local Python
python3 test_api.py

# Test with local setup
./test_local.sh

# Test with Docker
./test_docker.sh
```

### Manual Testing

1. **Health Check**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Start Analysis**
   ```bash
   curl -X POST http://localhost:8123/analyze-video/ \
     -H "X-API-Key: your_api_key_here" \
     -H "Content-Type: application/json" \
     -d '{"youtube_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"}'
   ```

3. **Check Status**
   ```bash
   curl http://localhost:8123/task-status/{task_id} \
     -H "X-API-Key: your_api_key_here"
   ```

## Deployment

### Hetzner/Coolify Deployment

The application is ready for deployment on Hetzner with Coolify. Here's what you need to know:

#### ✅ Ready for Deployment

- **Docker Support**: Fully containerized with proper Dockerfile
- **Environment Variables**: Configurable via environment variables
- **Health Checks**: Built-in health monitoring
- **Resource Management**: Proper memory and CPU limits
- **Security**: API key authentication
- **Logging**: Comprehensive logging for monitoring

#### 🔧 Deployment Steps

1. **Prepare Environment Variables**
   ```bash
   API_KEY=your_secure_api_key
   GEMINI_API_KEY=your_gemini_api_key
   USE_GCS_STORAGE=false  # Set to true for production
   ```

2. **Deploy to Coolify**
   - Create new service in Coolify
   - Use the Dockerfile from this repository
   - Set environment variables
   - Configure port 8123
   - Set resource limits (recommended: 2GB RAM, 1 CPU)

3. **Configure Domain/Proxy**
   - Set up reverse proxy to port 8000
   - Configure SSL certificates
   - Set up custom domain

#### 📊 Resource Requirements

- **Minimum**: 1GB RAM, 1 CPU
- **Recommended**: 2GB RAM, 2 CPU
- **Storage**: 1GB for temporary video files
- **Network**: Stable internet connection for YouTube downloads

#### 🔍 Monitoring

The application provides several monitoring endpoints:

- `/health` - Overall health status
- `/` - Basic availability check
- Built-in logging for task tracking

### Google Cloud Run Deployment

For Google Cloud Run deployment, use the provided scripts:

```bash
# Set up Google Cloud project
export GOOGLE_CLOUD_PROJECT=your-project-id
export DEPLOY_REGION=us-central1

# Run deployment script
./scripts/deploy.sh
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_KEY` | Yes | - | API key for authentication |
| `GEMINI_API_KEY` | Yes | - | Google Gemini API key |
| `USE_GCS_STORAGE` | No | false | Enable Google Cloud Storage |
| `GCS_BUCKET_NAME` | No | youtube-analyzer-temp-files | GCS bucket name |
| `GOOGLE_CLOUD_PROJECT` | No | - | Google Cloud project ID |

### API Authentication

All endpoints (except health checks) require API key authentication via the `X-API-Key` header.

## Troubleshooting

### Common Issues

1. **YouTube Download Failures**
   - YouTube may block automated access
   - Try different videos or implement cookie authentication
   - Check network connectivity

2. **Gemini API Errors**
   - Verify API key is correct
   - Check API quota limits
   - Ensure video file is valid

3. **Memory Issues**
   - Large videos may cause memory problems
   - Consider using cloud storage
   - Monitor resource usage

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Development

### Project Structure

```
youtube-analyzer/
├── fastapi_youtube_analyzer.py          # Production version
├── fastapi_youtube_analyzer_local_storage.py  # Development version
├── requirements.txt                      # Python dependencies
├── Dockerfile                           # Docker configuration
├── docker-compose.yml                   # Docker Compose setup
├── test_api.py                          # API test suite
├── test_local.sh                        # Local testing script
├── test_docker.sh                       # Docker testing script
├── deployment/                          # Deployment configurations
│   ├── service.yaml                     # Cloud Run service config
│   └── cloudbuild.yaml                  # Cloud Build config
└── scripts/                             # Deployment scripts
    └── deploy.sh                        # Google Cloud deployment
```

### Adding Features

1. **New Analysis Types**: Modify the Gemini prompt in `analyze_with_gemini()`
2. **Additional Storage**: Implement new storage backends
3. **Enhanced Security**: Add rate limiting, IP whitelisting
4. **Monitoring**: Integrate with monitoring services

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Test with different YouTube videos
4. Verify API keys and permissions
