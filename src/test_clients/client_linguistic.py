#!/usr/bin/env python3
"""
Test script to verify linguistic analysis is working correctly.
Demonstrates the linguistic analysis endpoint with polling.
"""

import requests
import json
import time
import sys

API_URL = "http://localhost:8000"
POLL_INTERVAL = 2
MAX_WAIT = 300


def poll_job_status(job_id: str, endpoint: str = "linguistic") -> dict:
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
                print(f"   raw response: {response.text}")
                raise Exception(data.get("error", "Job failed"))

            time.sleep(POLL_INTERVAL)
        except Exception as e:
            print(f"   ✗ Polling error: {e}")
            raise

    raise Exception(f"Job timed out after {MAX_WAIT}s")


def test_linguistic_analysis():
    """Test that linguistic analysis is working in API."""

    # Test text - a sample Chinese passage
    full_text = """北京是中国的首都，也是世界著名的历史文化名城。北京有着3000年的建城史和850年的建都史。在这漫长的历史岁月中，北京既是中国古代文明的中心，也是中世纪世界上最伟大的城市之一。"""

    # Selected text for analysis
    selected_text = "也是世界著名的历史文化名城"

    print("=" * 70)
    print("Linguistic Analysis Test")
    print("=" * 70)
    print(f"\nFull Text: {full_text}\n")
    print(f"Selected Text: {selected_text}\n")

    # 1. Submit async linguistic analysis job
    print("Submitting async linguistic analysis job")
    try:
        response = requests.post(
            f"{API_URL}/linguistic/async",
            json={"full_text": full_text, "selected_text": selected_text},
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
    print("Polling for linguistic analysis completion")
    try:
        data = poll_job_status(job_id, endpoint="linguistic")
    except Exception as e:
        print(f"   Linguistic analysis failed: {e}")
        print(f"Original json: {response.text}")
        return False

    print("   Linguistic analysis completed\n")

    # 3. Verify result structure
    print("Verifying result structure")
    result = data.get("result", {})

    if not result:
        print(f"   No result in response")
        return False

    # Check for required fields
    required_fields = [
        "analyzed_text",
        "english_translation",
        "sentence_structure_explanation",
        "grammatical_rule_explanation",
        "grammar_patterns",
    ]

    for field in required_fields:
        if field not in result:
            print(f"   ✗ Missing field: {field}")
            return False

    print(f"   All required fields present")

    # 4. Display analysis results
    print("\nLinguistic Analysis Results:\n")

    analyzed_text = result.get("analyzed_text", {})
    if analyzed_text:
        print(f"   Analyzed Text (Chinese): {analyzed_text.get('chinese', 'N/A')}")
        print(f"   Analyzed Text (Pinyin): {analyzed_text.get('pinyin', 'N/A')}")

    if result.get("expansion_note"):
        print(f"\n   Expansion Note: {result.get('expansion_note')}")

    print(f"\n   English Translation:\n   {result.get('english_translation', 'N/A')}")

    print(f"\n   Sentence Structure Explanation:")
    print(f"   {result.get('sentence_structure_explanation', 'N/A')}")

    print(f"\n   Grammatical Rule Explanation:")
    print(f"   {result.get('grammatical_rule_explanation', 'N/A')}")

    grammar_patterns = result.get("grammar_patterns", [])
    if grammar_patterns:
        print(f"\n   Grammar Patterns Found ({len(grammar_patterns)}):")
        for i, pattern in enumerate(grammar_patterns, 1):
            print(f"\n      Pattern {i}:")
            print(f"      Name: {pattern.get('pattern', 'N/A')}")
            print(f"      Structure: {pattern.get('structure', 'N/A')}")

            example = pattern.get("example_in_text", {})
            if example:
                print(f"      Example (Chinese): {example.get('chinese', 'N/A')}")
                print(f"      Example (Pinyin): {example.get('pinyin', 'N/A')}")

            print(f"      Explanation: {pattern.get('explanation', 'N/A')}")

    print("\n" + "=" * 70)
    print("PASSED: Linguistic Analysis Test")
    print("=" * 70)
    print("\nSummary:")
    print(f"  • Full text provided for context")
    print(f"  • Selected text analyzed: {selected_text}")
    print(f"  • Sentence structure breakdown provided")
    print(f"  • Grammatical rules explained")
    print(f"  • Grammar patterns identified: {len(grammar_patterns)}")
    print(f"  • English translation provided")
    if result.get("expansion_note"):
        print(f"  • Text expansion performed when needed")

    return True


def test_health_check():
    """Verify API is running."""
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


def test_multiple_selections():
    """Test linguistic analysis with different text selections."""
    print("\n\n" + "=" * 70)
    print("Multiple Selection Test")
    print("=" * 70)

    full_text = """北京是中国的首都，也是世界著名的历史文化名城。北京有着3000年的建城史和850年的建都史。"""

    selections = [
        "是中国的首都",
        "也是世界著名的历史文化名城",
        "有着3000年的建城史和850年的建都史",
    ]

    for i, selected_text in enumerate(selections, 1):
        print(f"\nTest {i}: {selected_text}")

        try:
            response = requests.post(
                f"{API_URL}/linguistic/async",
                json={"full_text": full_text, "selected_text": selected_text},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            job_id = data["job_id"]
            print(f"   Job ID: {job_id}")

            # Poll for completion
            result_data = poll_job_status(job_id, endpoint="linguistic")
            result = result_data.get("result", {})

            if result.get("success") is False:
                print(f"   ✗ Analysis failed: {result.get('error')}")
            else:
                analyzed = result.get("analyzed_text", {}).get("chinese", "N/A")
                print(f"   ✓ Analyzed: {analyzed}")

        except Exception as e:
            print(f"   ✗ Error: {e}")
            continue

    print("\n" + "=" * 70)
    print("Multiple Selection Test Complete")
    print("=" * 70)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("API Linguistic Analysis Verification")
    print("=" * 70)

    # Step 1: Health check
    if not test_health_check():
        print("\nAPI is not running. Start it with: python main.py")
        sys.exit(1)

    # Step 2: Run linguistic analysis test
    print("\n")
    if not test_linguistic_analysis():
        print("\nLinguistic analysis test failed")
        sys.exit(1)

    # Step 3: Run multiple selection test (optional, commented out by default)
    # test_multiple_selections()

    print("\n\nAll tests passed!")
    sys.exit(0)
