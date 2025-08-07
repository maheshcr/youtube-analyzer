#!/usr/bin/env python3
"""
Test script for YouTube Video Analyzer API
This script tests all endpoints and provides examples for usage.
"""

import requests
import json
import time
import os
from typing import Optional

class YouTubeAnalyzerTester:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        }
    
    def test_health_check(self) -> bool:
        """Test the health check endpoint"""
        print("🔍 Testing health check...")
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed: {data}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def test_root_endpoint(self) -> bool:
        """Test the root endpoint"""
        print("🔍 Testing root endpoint...")
        try:
            response = requests.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Root endpoint: {data}")
                return True
            else:
                print(f"❌ Root endpoint failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Root endpoint error: {e}")
            return False
    
    def test_analyze_video(self, youtube_url: str) -> Optional[str]:
        """Test video analysis endpoint"""
        print(f"🔍 Testing video analysis for: {youtube_url}")
        
        payload = {
            "youtube_url": youtube_url
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/analyze-video/",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                task_id = data.get('task_id')
                print(f"✅ Analysis started: {data}")
                return task_id
            else:
                print(f"❌ Analysis failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Analysis error: {e}")
            return None
    
    def test_task_status(self, task_id: str) -> bool:
        """Test task status endpoint"""
        print(f"🔍 Checking task status: {task_id}")
        
        try:
            response = requests.get(
                f"{self.base_url}/task-status/{task_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                print(f"✅ Task status: {status}")
                
                if status == 'completed':
                    result = data.get('result')
                    print(f"📊 Analysis result: {json.dumps(result, indent=2)}")
                    return True
                elif status == 'failed':
                    error = data.get('error')
                    print(f"❌ Task failed: {error}")
                    return False
                else:
                    print(f"⏳ Task still in progress: {status}")
                    return False
            else:
                print(f"❌ Status check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Status check error: {e}")
            return False
    
    def test_list_tasks(self) -> bool:
        """Test list tasks endpoint"""
        print("🔍 Testing list tasks...")
        
        try:
            response = requests.get(
                f"{self.base_url}/tasks",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Tasks list: {json.dumps(data, indent=2)}")
                return True
            else:
                print(f"❌ List tasks failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ List tasks error: {e}")
            return False
    
    def test_delete_task(self, task_id: str) -> bool:
        """Test delete task endpoint"""
        print(f"🔍 Testing delete task: {task_id}")
        
        try:
            response = requests.delete(
                f"{self.base_url}/task/{task_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Task deleted: {data}")
                return True
            else:
                print(f"❌ Delete task failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Delete task error: {e}")
            return False
    
    def wait_for_task_completion(self, task_id: str, max_wait_time: int = 600) -> bool:
        """Wait for task completion with timeout"""
        print(f"⏳ Waiting for task completion: {task_id}")
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                response = requests.get(
                    f"{self.base_url}/task-status/{task_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status')
                    
                    if status == 'completed':
                        result = data.get('result')
                        print(f"✅ Task completed successfully!")
                        print(f"📊 Analysis result: {json.dumps(result, indent=2)}")
                        return True
                    elif status == 'failed':
                        error = data.get('error')
                        print(f"❌ Task failed: {error}")
                        return False
                    else:
                        print(f"⏳ Task status: {status} (waiting...)")
                        time.sleep(10)  # Wait 10 seconds before checking again
                else:
                    print(f"❌ Status check failed: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ Status check error: {e}")
                return False
        
        print(f"⏰ Timeout reached after {max_wait_time} seconds")
        return False
    
    def run_full_test(self, youtube_url: str):
        """Run a complete test of the API"""
        print("🚀 Starting full API test...")
        print("=" * 50)
        
        # Test basic endpoints
        if not self.test_root_endpoint():
            return False
        
        if not self.test_health_check():
            return False
        
        # Test video analysis
        task_id = self.test_analyze_video(youtube_url)
        if not task_id:
            return False
        
        # Wait for completion
        if not self.wait_for_task_completion(task_id):
            return False
        
        # Test list tasks
        self.test_list_tasks()
        
        # Test delete task
        self.test_delete_task(task_id)
        
        print("=" * 50)
        print("✅ Full test completed successfully!")
        return True

def main():
    # Configuration
    base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
    api_key = os.getenv('API_KEY', 'dev_api_key_123')
    
    # Test YouTube URLs (famous videos that are likely to work)
    test_urls = [
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # Me at the zoo (first YouTube video)
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll (very short)
        "https://www.youtube.com/watch?v=9bZkp7q19f0",  # PSY - GANGNAM STYLE
    ]
    
    print("🧪 YouTube Analyzer API Test Suite")
    print("=" * 50)
    
    tester = YouTubeAnalyzerTester(base_url, api_key)
    
    # Test with each URL
    for i, url in enumerate(test_urls, 1):
        print(f"\n📹 Test {i}: {url}")
        print("-" * 30)
        
        success = tester.run_full_test(url)
        
        if success:
            print(f"✅ Test {i} passed!")
        else:
            print(f"❌ Test {i} failed!")
        
        # Wait between tests
        if i < len(test_urls):
            print("⏳ Waiting 5 seconds before next test...")
            time.sleep(5)

if __name__ == "__main__":
    main()
