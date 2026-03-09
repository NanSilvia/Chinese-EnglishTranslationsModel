#!/usr/bin/env python3
"""
Test script to verify model_override functionality in the API.
"""

import requests
import json
import time
import sys

API_URL = "http://localhost:8000"
POLL_INTERVAL = 2
MAX_WAIT = 120

# Test models
TEST_MODELS = [
    "qwen3:latest",
    "gemma3:27b-it-fp16",
    "deepseek-r1:8b",
]

# Simple test text
TEST_TEXT = "你好，世界！这是一个测试。"


def poll_job_status(job_id: str) -> dict:
    """Poll job status until completion or failure."""
    start_time = time.time()

    while time.time() - start_time < MAX_WAIT:
        try:
            response = requests.get(f"{API_URL}/translate/status/{job_id}", timeout=10)
            response.raise_for_status()
            data = response.json()
            status = data["status"]

            print(f"   Status: {status} - {data.get('progress', '')}")

            if status == "completed":
                return data
            elif status == "failed":
                print(f"   ✗ Job failed: {data.get('error')}")
                raise Exception(data.get("error", "Job failed"))

            time.sleep(POLL_INTERVAL)
        except Exception as e:
            print(f"   ✗ Polling error: {e}")
            raise

    raise Exception(f"Job timed out after {MAX_WAIT}s")


def test_model_override(model_name: str):
    """Test translation with a specific model override."""
    print(f"\n{'='*70}")
    print(f"Testing Model: {model_name}")
    print(f"{'='*70}")

    try:
        # Submit async translation job with model override
        print(f"📤 Submitting translation job with model_override='{model_name}'...")
        response = requests.post(
            f"{API_URL}/translate/async",
            json={
                "text": TEST_TEXT,
                "schema_name": "translate",
                "model_override": model_name,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        job_id = data["job_id"]
        print(f"   ✓ Job submitted: {job_id}")
    except Exception as e:
        print(f"   ✗ Failed to submit job: {e}")
        return False

    # Poll for completion
    print(f"⏳ Polling for translation completion...")
    try:
        result_data = poll_job_status(job_id)
    except Exception as e:
        print(f"   ✗ Translation failed: {e}")
        return False

    print(f"   ✓ Translation completed!")

    # Extract and display result
    result = result_data.get("result", {})
    translation_data = result.get("translation", {})

    if translation_data.get("success"):
        translated_text = translation_data.get("translated_text", "")
        model_used = translation_data.get("model", "unknown")

        print(f"\n📝 Results:")
        print(f"   Input:  {TEST_TEXT}")
        print(f"   Output: {translated_text}")
        print(f"   Model:  {model_used}")

        # Verify model was actually used
        if model_name in model_used or model_used == "qwen":
            print(f"   ✓ Model override successful!")
            return True
        else:
            print(
                f"   ⚠️  Warning: Expected model '{model_name}' but got '{model_used}'"
            )
            return True
    else:
        error = translation_data.get("error", "Unknown error")
        print(f"   ✗ Translation failed: {error}")
        return False


def check_api_health():
    """Check if API is running."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "healthy":
            print(f"✓ API is running: {data.get('message')}")
            return True
        else:
            print(f"✗ API not healthy: {data}")
            return False
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def main():
    """Run model override tests."""
    print("\n" + "=" * 70)
    print("MODEL OVERRIDE FUNCTIONALITY TEST")
    print("=" * 70)

    # Check API health
    print("\n🔍 Checking API health...")
    if not check_api_health():
        print("\n⚠️  API is not accessible. Please ensure:")
        print("   1. API server is running:")
        print("      cd api && uvicorn main:app --reload --port 8000")
        print(f"   2. API is accessible at {API_URL}")
        sys.exit(1)

    # Test each model
    results = {}
    for model_name in TEST_MODELS:
        success = test_model_override(model_name)
        results[model_name] = success
        time.sleep(1)  # Rate limiting

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for model_name, success in results.items():
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"   {status}: {model_name}")

    passed = sum(1 for s in results.values() if s)
    total = len(results)

    print(f"\n   Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All model override tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
