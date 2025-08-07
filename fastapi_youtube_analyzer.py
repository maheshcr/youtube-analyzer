from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Header
from fastapi.security import HTTPBearer
from pydantic import BaseModel, HttpUrl
import google.generativeai as genai
from google.cloud import storage
import yt_dlp
import os
import time
import uuid
import json
import tempfile
import shutil
from typing import Optional, Dict, Any
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="YouTube Video Content Analyzer",
    description="Analyze YouTube videos using Google's Gemini AI",
    version="1.0.0"
)

# Security
security = HTTPBearer()

# In-memory task storage (in production, use Redis or Firestore)
tasks: Dict[str, Dict[str, Any]] = {}

# Configuration
API_KEY = os.getenv("API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
USE_GCS_STORAGE = os.getenv("USE_GCS_STORAGE", "false").lower() == "true"
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "youtube-analyzer-temp-files")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

if not API_KEY:
    raise ValueError("API_KEY environment variable not set")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

# Initialize GCS client if using cloud storage
gcs_client = None
if USE_GCS_STORAGE:
    try:
        gcs_client = storage.Client(project=GOOGLE_CLOUD_PROJECT)
        bucket = gcs_client.bucket(GCS_BUCKET_NAME)
        logger.info(f"Using GCS bucket: {GCS_BUCKET_NAME}")
    except Exception as e:
        logger.error(f"Failed to initialize GCS client: {e}")
        USE_GCS_STORAGE = False

# Configure Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {e}")
    raise


# Pydantic models
class VideoAnalysisRequest(BaseModel):
    youtube_url: HttpUrl


class TaskResponse(BaseModel):
    message: str
    task_id: str


class TaskStatusResponse(BaseModel):
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Security dependency
def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# Helper functions
def is_valid_youtube_url(url: str) -> bool:
    """Validate if the URL is a valid YouTube URL"""
    youtube_domains = ["youtube.com", "youtu.be", "www.youtube.com", "m.youtube.com"]
    return any(domain in url for domain in youtube_domains)


def upload_to_gcs(local_path: str, blob_name: str) -> str:
    """Upload file to Google Cloud Storage"""
    if not USE_GCS_STORAGE:
        return local_path

    try:
        bucket = gcs_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(local_path)
        logger.info(f"File uploaded to GCS: gs://{GCS_BUCKET_NAME}/{blob_name}")
        return f"gs://{GCS_BUCKET_NAME}/{blob_name}"
    except Exception as e:
        logger.error(f"Failed to upload to GCS: {e}")
        return local_path


def download_from_gcs(gcs_path: str, local_path: str):
    """Download file from Google Cloud Storage"""
    if not gcs_path.startswith("gs://"):
        return

    try:
        # Parse GCS path
        path_parts = gcs_path.replace("gs://", "").split("/", 1)
        bucket_name = path_parts[0]
        blob_name = path_parts[1]

        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.download_to_filename(local_path)
        logger.info(f"File downloaded from GCS to {local_path}")
    except Exception as e:
        logger.error(f"Failed to download from GCS: {e}")
        raise


def cleanup_gcs_file(gcs_path: str):
    """Delete file from Google Cloud Storage"""
    if not gcs_path.startswith("gs://"):
        return

    try:
        path_parts = gcs_path.replace("gs://", "").split("/", 1)
        bucket_name = path_parts[0]
        blob_name = path_parts[1]

        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.delete()
        logger.info(f"File deleted from GCS: {gcs_path}")
    except Exception as e:
        logger.warning(f"Failed to delete from GCS: {e}")


def download_video(url: str, output_path: str) -> str:
    """Download video using yt-dlp with multiple fallback strategies"""

    # Strategy 1: Try with TV embedded client and no cookies
    ydl_opts_1 = {
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'format': 'worst[ext=mp4]/worst',  # Force mp4 and lowest quality
        'noplaylist': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['tv_embedded'],
                'player_skip': ['configs', 'webpage', 'js'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (SMART-TV; Linux; Tizen 2.4.0) AppleWebKit/538.1',
            'Accept': '*/*',
        },
        'retries': 2,
        'fragment_retries': 2,
        'sleep_interval': 5,
        'max_sleep_interval': 10,
        'ignoreerrors': False,
    }

    # Strategy 2: Try with mobile client
    ydl_opts_2 = {
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'format': 'worst[ext=mp4]/worst',
        'noplaylist': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android'],
                'player_skip': ['configs', 'webpage'],
            }
        },
        'http_headers': {
            'User-Agent': 'com.google.android.youtube/17.31.35 (Linux; U; Android 11) gzip',
        },
        'retries': 2,
        'sleep_interval': 3,
    }

    # Strategy 3: Try with web client and age bypass
    ydl_opts_3 = {
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'format': 'worst[ext=mp4]/worst',
        'noplaylist': True,
        'age_limit': 99,  # Bypass age restrictions
        'extractor_args': {
            'youtube': {
                'player_client': ['web'],
                'skip': ['dash', 'hls'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        },
        'retries': 1,
    }

    strategies = [
        ("TV Embedded Client", ydl_opts_1),
        ("Android Mobile Client", ydl_opts_2),
        ("Web Client with Age Bypass", ydl_opts_3),
    ]

    for strategy_name, ydl_opts in strategies:
        try:
            logger.info(f"Trying strategy: {strategy_name}")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'video')

                # Check if the video is available
                if info.get('availability') == 'private':
                    raise Exception(f"Video is private or unavailable")

                # Download the video
                ydl.download([url])

                # Find the downloaded file
                for file in os.listdir(output_path):
                    if any(ext in file.lower() for ext in ['.mp4', '.webm', '.mkv', '.avi']):
                        return os.path.join(output_path, file)

                raise Exception("Downloaded file not found")

        except Exception as e:
            logger.warning(f"Strategy '{strategy_name}' failed: {str(e)}")
            if strategy_name == strategies[-1][0]:  # Last strategy
                # If all strategies fail, try to get video info at least
                try:
                    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                        info = ydl.extract_info(url, download=False)
                        if info:
                            raise Exception(
                                f"All download strategies failed for video: '{info.get('title', 'Unknown')}'. YouTube may be blocking automated access. Try using a different video or implement cookie authentication.")
                except:
                    pass
                raise Exception(
                    f"All download strategies failed. YouTube is blocking automated access. Error from last attempt: {str(e)}")
            continue

    raise Exception("All download strategies failed")


def analyze_with_gemini(video_path: str) -> Dict[str, str]:
    """Analyze video content using Gemini"""
    # If it's a GCS path, download to local temp file for Gemini
    local_video_path = video_path
    temp_file = None

    if video_path.startswith("gs://"):
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        local_video_path = temp_file.name
        download_from_gcs(video_path, local_video_path)
        temp_file.close()

    try:
        if not os.path.exists(local_video_path):
            raise FileNotFoundError(f"Video file not found at '{local_video_path}'")

        logger.info(f"Uploading file to Gemini: {local_video_path}")

        # Upload the video file to Gemini
        video_file = genai.upload_file(path=local_video_path)

        logger.info(f"File uploaded. URI: {video_file.uri}")

        # Wait for processing to complete
        while video_file.state.name == "PROCESSING":
            time.sleep(10)
            video_file = genai.get_file(video_file.name)

        if video_file.state.name == "FAILED":
            raise Exception("Video processing failed in Gemini")

        logger.info("Video processed successfully. Analyzing content...")

        # Configure the model
        model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

        # Analysis prompt
        prompt = """
        Analyze the content of this video from the perspective of a marketing analyst.
        Based on the video's visual and audio content, please perform the following:
        1. Identify the main topic of the video.
        2. Provide a brief one-sentence summary.
        3. Categorize the video into the most relevant interest bucket from this list: 
           'Technology & Innovation', 'Entertainment & Pop Culture', 'Education & Learning', 
           'Lifestyle & Wellness', 'Gaming', 'Finance & Business', 'Travel & Adventure'.

        Please provide the output in a clean JSON format like this:
        {
          "topic": "The main subject of the video",
          "summary": "A concise one-sentence summary.",
          "interest_bucket": "The most fitting category from the list"
        }
        """

        try:
            # Generate content
            response = model.generate_content(
                [prompt, video_file],
                request_options={"timeout": 600}
            )

            # Clean and parse the response
            cleaned_response = response.text.replace("```json", "").replace("```", "").strip()
            result = json.loads(cleaned_response)

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            # Fallback: return raw response
            return {
                "topic": "Unable to parse analysis",
                "summary": response.text[:200] + "...",
                "interest_bucket": "Entertainment & Pop Culture"
            }
        except Exception as e:
            logger.error(f"Error during Gemini analysis: {e}")
            raise
        finally:
            # Clean up uploaded file from Gemini
            try:
                genai.delete_file(video_file.name)
                logger.info("Uploaded file deleted from Gemini")
            except Exception as e:
                logger.warning(f"Failed to delete file from Gemini: {e}")

    finally:
        # Clean up temporary file if created
        if temp_file and os.path.exists(local_video_path):
            os.unlink(local_video_path)


def process_video_task(task_id: str, youtube_url: str):
    """Background task to process video analysis"""
    temp_dir = None
    video_gcs_path = None

    try:
        # Update task status
        tasks[task_id]["status"] = "in_progress"
        tasks[task_id]["updated_at"] = datetime.now().isoformat()

        # Validate YouTube URL
        if not is_valid_youtube_url(str(youtube_url)):
            raise ValueError("Invalid YouTube URL provided")

        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Created temp directory: {temp_dir}")

        # Download video
        logger.info(f"Starting video download for task {task_id}")
        video_path = download_video(str(youtube_url), temp_dir)
        logger.info(f"Video downloaded successfully: {video_path}")

        # Upload to GCS if enabled
        if USE_GCS_STORAGE:
            blob_name = f"videos/{task_id}/{os.path.basename(video_path)}"
            video_gcs_path = upload_to_gcs(video_path, blob_name)
            analysis_video_path = video_gcs_path
        else:
            analysis_video_path = video_path

        # Analyze with Gemini
        logger.info(f"Starting Gemini analysis for task {task_id}")
        result = analyze_with_gemini(analysis_video_path)

        # Update task with result
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = result
        tasks[task_id]["updated_at"] = datetime.now().isoformat()

        logger.info(f"Task {task_id} completed successfully")

    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}")
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        tasks[task_id]["updated_at"] = datetime.now().isoformat()

    finally:
        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory: {e}")

        # Clean up GCS file after analysis
        if video_gcs_path:
            cleanup_gcs_file(video_gcs_path)


# API Endpoints (same as before)
@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "YouTube Video Content Analyzer API is running"}


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_tasks": len([t for t in tasks.values() if t["status"] == "in_progress"]),
        "using_gcs": USE_GCS_STORAGE,
        "gcs_bucket": GCS_BUCKET_NAME if USE_GCS_STORAGE else None
    }


@app.post("/analyze-video/", response_model=TaskResponse)
async def analyze_video_endpoint(
        request: VideoAnalysisRequest,
        background_tasks: BackgroundTasks,
        api_key: str = Depends(verify_api_key)
):
    """Start video analysis task"""
    task_id = str(uuid.uuid4())

    # Initialize task
    tasks[task_id] = {
        "status": "starting",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "youtube_url": str(request.youtube_url),
        "result": None,
        "error": None
    }

    # Start background task
    background_tasks.add_task(process_video_task, task_id, request.youtube_url)

    logger.info(f"Started analysis task {task_id} for URL: {request.youtube_url}")

    return TaskResponse(
        message="Video analysis started in the background.",
        task_id=task_id
    )


@app.get("/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
        task_id: str,
        api_key: str = Depends(verify_api_key)
):
    """Get task status and result"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]

    return TaskStatusResponse(
        status=task["status"],
        result=task.get("result"),
        error=task.get("error")
    )


@app.delete("/task/{task_id}")
async def delete_task(
        task_id: str,
        api_key: str = Depends(verify_api_key)
):
    """Delete a completed task"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]
    if task["status"] == "in_progress":
        raise HTTPException(status_code=400, detail="Cannot delete task in progress")

    del tasks[task_id]
    return {"message": f"Task {task_id} deleted successfully"}


@app.get("/tasks")
async def list_tasks(
        api_key: str = Depends(verify_api_key),
        status: Optional[str] = None
):
    """List all tasks, optionally filtered by status"""
    filtered_tasks = tasks

    if status:
        filtered_tasks = {
            task_id: task for task_id, task in tasks.items()
            if task["status"] == status
        }

    return {
        "total_tasks": len(filtered_tasks),
        "tasks": {
            task_id: {
                "status": task["status"],
                "created_at": task["created_at"],
                "updated_at": task["updated_at"],
                "youtube_url": task["youtube_url"]
            }
            for task_id, task in filtered_tasks.items()
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)