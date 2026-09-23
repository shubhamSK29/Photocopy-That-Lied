"""Test the backend API with demo images."""

import requests
from pathlib import Path

API_URL = "http://localhost:8000"

demo_dir = Path("demo")
demo_images = list(demo_dir.glob("*.jpg"))

print("Testing Backend API...")
print(f"API URL: {API_URL}")
print(f"Demo images: {len(demo_images)}")
print()

# Try to check if backend is running
try:
    response = requests.get(f"{API_URL}/api/config", timeout=5)
    print(f"Backend status: Running")
    print(f"Config: {response.json()}")
except requests.exceptions.ConnectionError:
    print("Backend is not running. Start it with:")
    print("  cd backend && python -m uvicorn main:app --reload --port 8000")
    exit(1)

print()
print("Testing image analysis...")

for image_path in demo_images:
    print(f"\nAnalyzing: {image_path.name}")
    
    with open(image_path, "rb") as f:
        files = {"file": (image_path.name, f, "image/jpeg")}
        try:
            response = requests.post(f"{API_URL}/api/analyze", files=files, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"  [OK] Analysis complete")
                print(f"  Risk score: {result.get('manipulation_evidence', 'N/A')}")
                print(f"  Risk band: {result.get('risk_band', 'N/A')}")
                print(f"  Analysis ID: {result.get('analysis_id', 'N/A')}")
            else:
                print(f"  [FAIL] Error: {response.status_code}")
                print(f"  Detail: {response.text}")
        except Exception as e:
            print(f"  [FAIL] Exception: {e}")

print("\nAPI test complete.")
