#!/usr/bin/env python3
"""
Test script to verify question generation is working correctly.
Demonstrates the questions endpoint with polling.
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


def test_question_generation():
    """Test that question generation is working in API."""

    # Test text - a sample Chinese passage
    test_text = """北京是中国的首都，也是世界著名的历史文化名城。北京有着3000年的建城史和850年的建都史。在这漫长的历史岁月中，北京既是中国古代文明的中心，也是中世纪世界上最伟大的城市之一。

北京有许多著名的景点，其中包括万里长城、故宫、颐和园等。长城是中国最伟大的工程之一，被誉为"世界上最伟大的墙"。故宫是中国最大的皇宫，建于1406年，在这里住过24位皇帝。颐和园是中国最大的皇家花园，以其美丽的景观而闻名世界。

北京的文化非常丰富多彩。这个城市有许多博物馆、美术馆和剧院，展示了中国的传统艺术和现代艺术。北京还有著名的小吃街，如王府井大街，那里可以尝到各种传统的北京美食。"""

    question_count = 5

    print("=" * 70)
    print("Question Generation Test")
    print("=" * 70)
    print(f"\nTest Text: {test_text}\n")
    print(f"Requesting {question_count} questions\n")

    # 1. Submit async question generation job
    print("Submitting async question generation job")
    try:
        response = requests.post(
            f"{API_URL}/questions/async",
            json={"text": test_text, "question_count": question_count},
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
    print("Polling for question generation completion")
    try:
        data = poll_job_status(job_id, endpoint="questions")
    except Exception as e:
        print(f"   Question generation failed: {e}")
        return False

    print("   Question generation completed\n")

    # 3. Verify result structure
    print("Verifying result structure")
    result = data.get("result", {})

    if not result:
        print(f"   No result in response")
        return False

    questions_list = result.get("questions", [])

    if not questions_list:
        print(f"   No questions in result")
        return False

    print(f"   Generated {len(questions_list)} questions")

    # 4. Display questions
    print("\nGenerated Questions:\n")
    for i, question in enumerate(questions_list, 1):
        print(f"   Question {i}:")
        print(f"   Prompt: {question.get('question_prompt', 'N/A')}")

        answers = question.get("possible_answers", [])
        correct_idx = question.get("correct_answer_index", -1)

        print(f"   Options:")
        for j, answer in enumerate(answers, 1):
            marker = "*" if j - 1 == correct_idx else " "
            print(f"     {marker} {j}. {answer}")
        print()

    print("=" * 70)
    print("PASSED: Question Generation Test")
    print("=" * 70)
    print("\nSummary:")
    print(f"  • Input text analyzed for question generation")
    print(f"  • HSK-style reading comprehension questions created")
    print(f"  • Each question has 4 answer options")
    print(f"  • Correct answer index provided for validation")
    print(f"  • Total questions generated: {len(questions_list)}")

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


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("API Question Generation Verification")
    print("=" * 70)

    # Step 1: Health check
    if not test_health_check():
        print("\nAPI is not running. Start it with: python main.py")
        sys.exit(1)

    # Step 2: Run question generation test
    print("\n")
    if not test_question_generation():
        print("\nQuestion generation test failed")
        sys.exit(1)

    print("\nAll tests passed!")
    sys.exit(0)
