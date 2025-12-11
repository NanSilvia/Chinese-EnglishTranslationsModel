"""
Test script for word analysis API endpoint.
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_word_analysis():
    """Test the /word/analyze endpoint."""
    print("\n=== Testing Word Analysis Endpoint ===\n")

    # Test 1: Chinese word with context
    print("Test 1: Chinese word '高兴' with context")
    payload = {
        "word": "高兴",
        "context": "我今天很高兴。",
        "language": "chi",
        "include_synonyms": True,
        "include_antonyms": True,
        "include_alternatives": True,
    }

    response = requests.post(
        f"{BASE_URL}/word/analyze",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"\nWord: {data['word']}")
        print(f"Context: {data['context']}")
        print(f"\nExplanation: {data['explanation']}")
        print(f"\nSynonyms ({len(data['synonyms'])}): {', '.join(data['synonyms'])}")
        print(f"Antonyms ({len(data['antonyms'])}): {', '.join(data['antonyms'])}")
        print(
            f"Alternative Wordings ({len(data['alternative_wordings'])}): {', '.join(data['alternative_wordings'])}"
        )
        print(f"\nUsage Examples:")
        for i, example in enumerate(data["usage_examples"], 1):
            print(f"  {i}. {example}")
    else:
        print(f"Error: {response.text}")

    # Test 2: Chinese word without context
    print("\n\nTest 2: Chinese word '学习' without context")
    payload = {
        "word": "学习",
        "language": "chi",
        "include_synonyms": True,
        "include_antonyms": True,
        "include_alternatives": True,
    }

    response = requests.post(
        f"{BASE_URL}/word/analyze",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"\nWord: {data['word']}")
        print(f"\nExplanation: {data['explanation']}")
        print(f"\nSynonyms: {', '.join(data['synonyms'])}")
        print(f"Antonyms: {', '.join(data['antonyms'])}")
        print(f"Alternative Wordings: {', '.join(data['alternative_wordings'])}")
    else:
        print(f"Error: {response.text}")

    # Test 3: English word
    print("\n\nTest 3: English word 'happy' with context")
    payload = {
        "word": "happy",
        "context": "I am very happy today.",
        "language": "eng",
        "include_synonyms": True,
        "include_antonyms": True,
        "include_alternatives": True,
    }

    response = requests.post(
        f"{BASE_URL}/word/analyze",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"\nWord: {data['word']}")
        print(f"Context: {data['context']}")
        print(f"\nExplanation: {data['explanation']}")
        print(f"\nSynonyms: {', '.join(data['synonyms'])}")
        print(f"Antonyms: {', '.join(data['antonyms'])}")
        print(f"Alternative Wordings: {', '.join(data['alternative_wordings'])}")
    else:
        print(f"Error: {response.text}")

    # Test 4: Only synonyms
    print("\n\nTest 4: Only synonyms for '困难'")
    payload = {
        "word": "困难",
        "context": "这个问题很困难。",
        "language": "chi",
        "include_synonyms": True,
        "include_antonyms": False,
        "include_alternatives": False,
    }

    response = requests.post(
        f"{BASE_URL}/word/analyze",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"\nWord: {data['word']}")
        print(f"Synonyms only: {', '.join(data['synonyms'])}")
        print(f"Antonyms: {data['antonyms']} (should be empty)")
        print(f"Alternatives: {data['alternative_wordings']} (should be empty)")
    else:
        print(f"Error: {response.text}")


if __name__ == "__main__":
    test_word_analysis()
