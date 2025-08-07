#!/bin/bash
# Deployment script for Google Cloud Run

set -e  # Exit on any error

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"your-project-id"}
SERVICE_NAME="youtube-analyzer"
REGION=${DEPLOY_REGION:-"us-central1"}
BUCKET_NAME="${PROJECT_ID}-youtube-analyzer-temp"

echo "🚀 Starting deployment to Google Cloud Run..."

# Check if required tools are installed
command -v gcloud >/dev/null 2>&1 || { echo "❌ gcloud CLI is required but not installed."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed."; exit 1; }

# Set the project
echo "📋 Setting project to $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required Google Cloud APIs..."
gcloud services enable run.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Create GCS bucket if it doesn't exist
echo "📦 Creating GCS bucket if needed..."
gsutil mb gs://$BUCKET_NAME 2>/dev/null || echo "Bucket already exists"

# Set bucket lifecycle policy
echo "🗑️ Setting bucket lifecycle policy..."
cat > /tmp/lifecycle.json << EOF
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {"age": 1}
    }
  ]
}
EOF
gsutil lifecycle set /tmp/lifecycle.json gs://$BUCKET_NAME

# Create secrets (if they don't exist)
echo "🔐 Creating secrets..."
if ! gcloud secrets describe youtube-analyzer-api-key >/dev/null 2>&1; then
    echo "Enter your API key:"
    read -s API_KEY
    echo "$API_KEY" | gcloud secrets create youtube-analyzer-api-key --data-file=-
fi

if ! gcloud secrets describe youtube-analyzer-gemini-key >/dev/null 2>&1; then
    echo "Enter your Gemini API key:"
    read -s GEMINI_KEY
    echo "$GEMINI_KEY" | gcloud secrets create youtube-analyzer-gemini-key --data-file=-
fi

# Create service account
echo "👤 Creating service account..."
gcloud iam service-accounts create youtube-analyzer-sa --display-name="YouTube Analyzer Service Account" 2>/dev/null || echo "Service account already exists"

# Grant permissions
echo "🔑 Granting IAM permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:youtube-analyzer-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectCreator"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:youtube-analyzer-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Build and deploy
echo "🏗️ Building and deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --source . \
    --region $REGION \
    --platform managed \
    --memory 4Gi \
    --cpu 2 \
    --timeout 3600 \
    --max-instances 20 \
    --min-instances 0 \
    --allow-unauthenticated \
    --port 8000 \
    --service-account youtube-analyzer-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --set-env-vars USE_GCS_STORAGE=true,GCS_BUCKET_NAME=$BUCKET_NAME,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,ENVIRONMENT=production \
    --set-secrets API_KEY=youtube-analyzer-api-key:latest,GEMINI_API_KEY=youtube-analyzer-gemini-key:latest

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)")

echo "✅ Deployment completed successfully!"
echo "🌍 Service URL: $SERVICE_URL"
echo "📖 API Documentation: $SERVICE_URL/docs"
echo "❤️ Health Check: $SERVICE_URL/health"

# Test the deployment
echo "🧪 Testing deployment..."
curl -f "$SERVICE_URL/health" || echo "❌ Health check failed"

echo "🎉 Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Test your API: curl -X POST '$SERVICE_URL/analyze-video/' -H 'X-API-Key: YOUR_KEY' -H 'Content-Type: application/json' -d '{\"youtube_url\": \"https://www.youtube.com/watch?v=jNQXAC9IVRw\"}'"
echo "2. Monitor logs: gcloud logs tail 'projects/$PROJECT_ID/logs/run.googleapis.com%2Fstdout' --filter='resource.labels.service_name=$SERVICE_NAME'"
echo "3. View metrics in Google Cloud Console"