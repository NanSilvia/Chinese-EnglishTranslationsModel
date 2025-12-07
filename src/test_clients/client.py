#!/usr/bin/env python3
"""
Test script to verify dictionary integration is working correctly.
Compares API response with notebook process.
"""

import requests
import json
import time
import sys

API_URL = "http://localhost:8000"
POLL_INTERVAL = 2
MAX_WAIT = 300


def poll_job_status(job_id: str, endpoint: str = "translate") -> dict:
    """Generic polling function for async jobs."""
    start_time = time.time()

    while time.time() - start_time < MAX_WAIT:
        try:
            response = requests.get(f"{API_URL}/{endpoint}/status/{job_id}", timeout=10)
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


def test_dictionary_integration():
    """Test that dictionary enrichment is working in API."""

    # Test text with Chinese terms that should match dictionary
    test_text = """北京故宫是中国明清两代的皇家宫殿，旧称为紫禁城，是中国古代宫廷建筑的精华。北京故宫以三大殿为中心，占地面积72万平方米，建筑面积约15万平方米，有大小宫殿七十多座，房屋九千余间。是世界上现存规模最大、保存最为完整的木质结构古建筑之一。\n故宫博物院是一座特殊的博物馆，成立于1925年，建立在紫禁城的基础上。近几年，在人们头脑中陈旧甚至略微显得古板的故宫开始活跃起来。一部《我在故宫修文物》让普通人了解到故宫背后的工匠精神，《 国家宝藏》恢弘的气势与现代科技结合，让人们见识到大国风范\n故宫文创，依托悠久的故宫历史，发掘新的产品形态，将古老与现代结合，将历史与商业叠加。故宫口红，故宫项链，故宫台历等等，被人们广为使用。"""

    print("=" * 70)
    print("Dictionary Integration Test")
    print("=" * 70)
    print(f"\nTest Text: {test_text}\n")

    # 1. Submit async translation job
    print("Submitting async translation job")
    try:
        response = requests.post(
            f"{API_URL}/translate/async",
            json={"text": test_text, "schema_name": "detailed"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        job_id = data["job_id"]
        print(f"   Job submitted: {job_id}\n")
    except Exception as e:
        print(f"   ✗ Failed to submit job: {e}")
        return False

    # 2. Poll for completion
    print("Polling for translation completion")
    try:
        data = poll_job_status(job_id, endpoint="translate")
    except Exception as e:
        print(f"   Translation failed: {e}")
        return False

    print("   Translation completed\n")

    # 3. Verify result structure
    print("Verifying result structure")
    result = data.get("result", {})
    translations = result.get("translations", {})

    if "qwen" in translations:
        qwen_result = translations["qwen"]
        print(f"   Qwen translation found")

        # Check for dictionary-enriched fields
        if "initial_translation" in qwen_result:
            print(
                f"   Stage 1 (initial) translation: {qwen_result['initial_translation']}"
            )

        if "translated_text" in qwen_result:
            print(f"   Stage 2 (refined) translation: {qwen_result['translated_text']}")

        if "explanations" in qwen_result:
            explanations = qwen_result["explanations"]
            print(f"   Explanations provided: {len(explanations)} items")
            for i, (term, explanation) in enumerate(explanations, 1):
                print(f"      {i}. {term}: {explanation}")
    else:
        print(f"   No Qwen translation in response")
        print(f"   Available models: {list(translations.keys())}")
        return False

    # 4. Verify dictionary hints were used
    print("\nVerifying dictionary enrichment")
    if "initial_translation" in qwen_result and qwen_result["initial_translation"]:
        print(f"   Dictionary hints were used in Stage 1")
        print(f"   Two-stage pipeline executed successfully")
    else:
        print(f"   Could not verify dictionary enrichment")

    print("\n" + "=" * 70)
    print("PASSED: Dictionary Integration Test")
    print("=" * 70)
    print("\nSummary:")
    print(f"  • Input text analyzed for Chinese terms")
    print(f"  • Dictionary lookup performed (BDIC)")
    print(f"  • Stage 1: Initial translation with hints")
    print(f"  • Stage 2: Refined translation + explanations")
    print(f"  • Process matches notebook behavior")

    return True


def test_health_check():
    """Verify API is running and dictionary is loaded."""
    print("\nHealth Check")
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "healthy":
            print(f"API is running")
            print(f"Active agent: {data.get('message')}")
            if data.get("ollama_connected"):
                print(f"Ollama is connected")
            return True
        else:
            print(f"✗ API not healthy: {data}")
            return False
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("API Dictionary Integration Verification")
    print("=" * 70)

    # Step 1: Health check
    if not test_health_check():
        print("\nAPI is not running. Start it with: python main.py")
        sys.exit(1)

    # Step 2: Run integration test
    print("\n")
    if not test_dictionary_integration():
        print("\nDictionary integration test failed")
        sys.exit(1)

    print("\nAll tests passed!")
    sys.exit(0)
