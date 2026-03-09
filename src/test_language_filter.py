#!/usr/bin/env python3
"""
Test script for language filtering in book search.
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_language_filter():
    """Test language filtering for Chinese books."""
    print("\n" + "=" * 70)
    print(" Testing Language Filter - Chinese Books Only")
    print("=" * 70)

    # Test 1: Search for Chinese language books
    print("\n1. Searching for Chinese books about history...")
    response = requests.post(
        f"{BASE_URL}/books/search",
        json={"query": "history", "limit": 5, "language": "chi"},
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Found: {data['num_found']} Chinese books")
        print(f"\nTop {len(data['results'])} results:")

        for i, book in enumerate(data["results"], 1):
            print(f"\n{i}. {book['title']}")
            print(f"   Authors: {', '.join(book['authors'])}")
            print(f"   Languages: {', '.join(book['language'])}")
            print(f"   Year: {book['first_publish_year']}")

    # Test 2: Search for English books
    print("\n" + "=" * 70)
    print("\n2. Searching for English books about Chinese philosophy...")
    response = requests.post(
        f"{BASE_URL}/books/search",
        json={"query": "Chinese philosophy", "limit": 5, "language": "eng"},
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Found: {data['num_found']} English books")
        print(f"\nTop {len(data['results'])} results:")

        for i, book in enumerate(data["results"], 1):
            print(f"\n{i}. {book['title']}")
            print(f"   Authors: {', '.join(book['authors'])}")
            print(f"   Languages: {', '.join(book['language'])}")

    # Test 3: Compare with no language filter
    print("\n" + "=" * 70)
    print("\n3. Searching WITHOUT language filter (all languages)...")
    response = requests.post(
        f"{BASE_URL}/books/search", json={"query": "Chinese literature", "limit": 5}
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Found: {data['num_found']} books (all languages)")
        print(f"\nLanguage distribution in results:")

        lang_count = {}
        for book in data["results"]:
            for lang in book["language"]:
                lang_count[lang] = lang_count.get(lang, 0) + 1

        for lang, count in sorted(lang_count.items(), key=lambda x: x[1], reverse=True):
            print(f"   {lang}: {count} books")

    print("\n" + "=" * 70)
    print(" Language Filter Tests Complete!")
    print("=" * 70)

    print("\n💡 Language codes:")
    print("   chi - Chinese")
    print("   eng - English")
    print("   jpn - Japanese")
    print("   fre - French")
    print("   spa - Spanish")
    print("   ger - German")


if __name__ == "__main__":
    try:
        test_language_filter()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to API server")
        print("Make sure the server is running: python main.py")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
