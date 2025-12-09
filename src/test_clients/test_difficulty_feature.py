"""
Test script for text difficulty analysis feature.
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_similar_difficulty_endpoint():
    """Test the /books/similar-difficulty endpoint."""
    print("\n=== Testing Text Difficulty Analysis Endpoint ===\n")

    # Test 1: Beginner Chinese text
    print("Test 1: Beginner Chinese text")
    beginner_text = "我喜欢看书。今天天气很好。"

    payload = {"original_text": beginner_text, "language": "chi", "limit": 3}

    response = requests.post(
        f"{BASE_URL}/books/similar-difficulty",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"\nDifficulty Analysis:")
        print(f"  - Difficulty Level: {data['difficulty_metrics']['difficulty_level']}")
        print(f"  - Complexity Score: {data['difficulty_metrics']['complexity_score']}")
        print(f"  - Character Count: {data['difficulty_metrics']['character_count']}")
        print(f"  - Word Count: {data['difficulty_metrics']['word_count']}")
        print(f"\nFound {data['num_found']} similar texts")
        print(f"Showing {len(data['similar_texts'])} results:")
        for i, text in enumerate(data["similar_texts"], 1):
            print(f"\n  {i}. {text['title']}")
            print(f"     Authors: {', '.join(text['authors'])}")
            print(f"     Language: {text['language']}")
            print(f"     Difficulty: {text['difficulty_metrics']['difficulty_level']}")
            print(f"     Complexity: {text['difficulty_metrics']['complexity_score']}")
    else:
        print(f"Error: {response.text}")

    # Test 2: Advanced Chinese text
    print("\n\nTest 2: Advanced Chinese text")
    advanced_text = "北京故宫是中国明清两代的皇家宫殿，旧称紫禁城，位于北京中轴线的中心。故宫以三大殿为中心，占地面积约72万平方米，建筑面积约15万平方米，有大小宫殿七十多座，房屋九千余间。"

    payload = {"original_text": advanced_text, "language": "chi", "limit": 3}

    response = requests.post(
        f"{BASE_URL}/books/similar-difficulty",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"\nDifficulty Analysis:")
        print(f"  - Difficulty Level: {data['difficulty_metrics']['difficulty_level']}")
        print(f"  - Complexity Score: {data['difficulty_metrics']['complexity_score']}")
        print(f"  - Character Count: {data['difficulty_metrics']['character_count']}")
        print(f"  - Word Count: {data['difficulty_metrics']['word_count']}")
        print(f"\nFound {data['num_found']} similar texts")
        print(f"Showing {len(data['similar_texts'])} results:")
        for i, text in enumerate(data["similar_texts"], 1):
            print(f"\n  {i}. {text['title']}")
            print(f"     Authors: {', '.join(text['authors'])}")
            print(f"     Language: {text['language']}")
            print(f"     Difficulty: {text['difficulty_metrics']['difficulty_level']}")
    else:
        print(f"Error: {response.text}")

    # Test 3: English text
    print("\n\nTest 3: English text")
    english_text = "The quick brown fox jumps over the lazy dog."

    payload = {"original_text": english_text, "language": "eng", "limit": 3}

    response = requests.post(
        f"{BASE_URL}/books/similar-difficulty",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"\nDifficulty Analysis:")
        print(f"  - Difficulty Level: {data['difficulty_metrics']['difficulty_level']}")
        print(f"  - Complexity Score: {data['difficulty_metrics']['complexity_score']}")
        print(f"  - Character Count: {data['difficulty_metrics']['character_count']}")
        print(f"  - Word Count: {data['difficulty_metrics']['word_count']}")
        print(f"\nFound {data['num_found']} similar texts")
    else:
        print(f"Error: {response.text}")


if __name__ == "__main__":
    test_similar_difficulty_endpoint()
