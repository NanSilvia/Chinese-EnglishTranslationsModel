#!/usr/bin/env python3
"""
Quick test to verify detailed schema returns correct JSON structure.
"""

import requests
import json
import time

API_URL = "http://localhost:8000"


def test_detailed_schema():
    """Test detailed schema format."""
    test_text = "北京故宫是中国明清两代的皇家宫殿"

    print("Testing Detailed Schema")
    print(f"Input: {test_text}\n")

    # Submit async job with detailed schema
    response = requests.post(
        f"{API_URL}/translate/async",
        json={"text": test_text, "schema_name": "detailed"},
        timeout=10,
    )

    job_id = response.json()["job_id"]
    print(f"Job ID: {job_id}\n")

    # Wait for completion
    while True:
        response = requests.get(f"{API_URL}/translate/status/{job_id}", timeout=10)
        data = response.json()

        if data["status"] == "completed":
            break
        elif data["status"] == "failed":
            print(f"Failed: {data.get('error')}")
            return

        print(f"Status: {data['status']}")
        time.sleep(2)

    # Print the result
    result = data.get("result", {})
    translations = result.get("translations", {})
    qwen_result = translations.get("qwen", {})

    print("\n" + "=" * 70)
    print("DETAILED SCHEMA RESPONSE")
    print("=" * 70)
    print(json.dumps(qwen_result, indent=2, ensure_ascii=False))

    # Check for expected keys
    print("\n" + "=" * 70)
    print("EXPECTED FIELDS FOR DETAILED SCHEMA")
    print("=" * 70)

    expected_fields = [
        "translated_text",
        "grammatical_analysis",
        "challenging_phrases",
        "cultural_context",
        "stylistic_notes",
        "alternative_interpretations",
    ]

    for field in expected_fields:
        if field in qwen_result:
            value = qwen_result[field]
            if isinstance(value, str):
                print(f"X {field}: {value}")
            else:
                print(f"X {field}: {json.dumps(value)[:100]}")
        else:
            print(f"{field}: MISSING")


if __name__ == "__main__":
    test_detailed_schema()
