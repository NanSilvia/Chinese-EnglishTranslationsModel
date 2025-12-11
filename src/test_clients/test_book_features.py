#!/usr/bin/env python3
"""
Test script for OpenLibrary book search and research endpoints.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def test_book_search():
    """Test basic book search."""
    print_section("TEST 1: Book Search")

    response = requests.post(
        f"{BASE_URL}/books/search",
        json={"query": "Chinese history", "limit": 3, "subject": "history"},
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Found: {data['num_found']} books")
    print(f"\nTop {len(data['results'])} results:")

    for i, book in enumerate(data["results"], 1):
        print(f"\n{i}. {book['title']}")
        print(f"   Authors: {', '.join(book['authors'])}")
        print(f"   Year: {book['first_publish_year']}")
        print(f"   Subjects: {', '.join(book['subjects'][:3])}")


def test_book_recommendations():
    """Test book recommendations from text."""
    print_section("TEST 2: Book Recommendations")

    text = """
    I'm fascinated by ancient Chinese philosophy, particularly Confucianism and Taoism.
    I want to understand the historical context and how these philosophies influenced
    Chinese culture and governance.
    """

    response = requests.post(
        f"{BASE_URL}/books/recommend", json={"text": text, "limit": 5}
    )

    print(f"Status: {response.status_code}")
    data = response.json()

    print(f"Text length: {data['text_length']} characters")
    print(f"Keywords: {', '.join(data['keywords'])}")
    print(f"Found: {data['num_found']} related books")
    print(f"\nTop {len(data['recommendations'])} recommendations:")

    for i, book in enumerate(data["recommendations"], 1):
        print(f"\n{i}. {book['title']}")
        print(f"   Authors: {', '.join(book['authors'])}")
        if book["subjects"]:
            print(f"   Subjects: {', '.join(book['subjects'][:3])}")


def test_text_research():
    """Test translation + book research."""
    print_section("TEST 3: Text Research (Translation + Books)")

    chinese_text = "北京故宫是中国明清两代的皇家宫殿，建于1406年到1420年。"

    print(f"Original text: {chinese_text}")
    print("\nSubmitting research request...")

    response = requests.post(
        f"{BASE_URL}/books/research", json={"original_text": chinese_text, "limit": 5}
    )

    print(f"Status: {response.status_code}")
    data = response.json()

    print(f"\nTranslation: {data['translated_text']}")
    print(f"Keywords: {', '.join(data['keywords'])}")
    print(f"Found: {data['num_books_found']} related books")
    print(f"\nRecommended books for further reading:")

    for i, book in enumerate(data["book_recommendations"], 1):
        print(f"\n{i}. {book['title']}")
        print(f"   Authors: {', '.join(book['authors'])}")
        if book["first_publish_year"]:
            print(f"   Published: {book['first_publish_year']}")
        if book["subjects"]:
            print(f"   Subjects: {', '.join(book['subjects'][:3])}")


def test_subject_browse():
    """Test browsing by subject."""
    print_section("TEST 4: Browse by Subject")

    subject = "chinese-literature"
    response = requests.get(f"{BASE_URL}/books/subject/{subject}?limit=3")

    print(f"Status: {response.status_code}")
    data = response.json()

    print(f"Subject: {data['subject']}")
    print(f"Found: {data['num_found']} books")
    print(f"\nSample books:")

    for i, book in enumerate(data["books"], 1):
        print(f"\n{i}. {book['title']}")
        print(f"   Authors: {', '.join(book.get('authors', ['Unknown']))}")


def test_author_search():
    """Test searching by author."""
    print_section("TEST 5: Search by Author")

    author = "Lu Xun"
    response = requests.get(f"{BASE_URL}/books/author/{author}?limit=3")

    print(f"Status: {response.status_code}")
    data = response.json()

    print(f"Author: {data['author']}")
    print(f"Found: {data['num_found']} books")
    print(f"\nBooks by {author}:")

    for i, book in enumerate(data["books"], 1):
        print(f"\n{i}. {book['title']}")
        if book.get("first_publish_year"):
            print(f"   Year: {book['first_publish_year']}")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print(" OpenLibrary Book Search & Research API Tests")
    print("=" * 70)

    try:
        # Test 1: Basic search
        test_book_search()
        time.sleep(1)

        # Test 2: Text-based recommendations
        test_book_recommendations()
        time.sleep(1)

        # Test 3: Translation + research
        test_text_research()
        time.sleep(1)

        # Test 4: Subject browsing
        test_subject_browse()
        time.sleep(1)

        # Test 5: Author search
        test_author_search()

        print("\n" + "=" * 70)
        print(" All tests completed!")
        print("=" * 70)

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to API server")
        print("Make sure the server is running: python main.py")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")


if __name__ == "__main__":
    main()
