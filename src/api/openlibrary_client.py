"""
OpenLibrary API client for book search and information retrieval.
"""

import requests
from typing import List, Dict, Any, Optional
import re

# OpenLibrary API endpoints
OPENLIBRARY_SEARCH_API = "https://openlibrary.org/search.json"
OPENLIBRARY_WORKS_API = "https://openlibrary.org/works"
OPENLIBRARY_AUTHORS_API = "https://openlibrary.org/authors"
OPENLIBRARY_SUBJECTS_API = "https://openlibrary.org/subjects"
OPENLIBRARY_COVER_API = "https://covers.openlibrary.org/b"


class OpenLibraryClient:
    """Client for interacting with OpenLibrary.org API."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Translation-Analysis-API/2.0 (Educational Tool)"}
        )

    def search_books(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        limit: int = 10,
        offset: int = 0,
        **filters,
    ) -> Dict[str, Any]:
        """
        Search books using OpenLibrary Search API.

        Args:
            query: Search query string
            fields: Specific fields to return
            limit: Maximum number of results (default: 10)
            offset: Starting offset for pagination
            **filters: Additional filters (author, subject, place, person, language, etc.)

        Returns:
            Search results dictionary with 'numFound' and 'docs'
        """
        params = {
            "q": query,
            "limit": limit,
            "offset": offset,
        }

        if fields:
            params["fields"] = ",".join(fields)

        # Handle language filter specially - needs to be added to query string
        language = filters.pop("language", None)
        if language:
            params["q"] = f"{query} language:{language}"

        for key, value in filters.items():
            if value:
                params[key] = value

        try:
            response = self.session.get(
                OPENLIBRARY_SEARCH_API, params=params, timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e), "numFound": 0, "docs": []}

    def get_work_details(self, work_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific work.

        Args:
            work_id: OpenLibrary work ID (e.g., "OL45883W" or "/works/OL45883W")

        Returns:
            Work details dictionary
        """
        work_id = work_id.replace("/works/", "")
        url = f"{OPENLIBRARY_WORKS_API}/{work_id}.json"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def get_author_details(self, author_id: str) -> Dict[str, Any]:
        """
        Get detailed information about an author.

        Args:
            author_id: OpenLibrary author ID (e.g., "OL23919A" or "/authors/OL23919A")

        Returns:
            Author details dictionary
        """
        author_id = author_id.replace("/authors/", "")
        url = f"{OPENLIBRARY_AUTHORS_API}/{author_id}.json"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def search_by_subject(self, subject: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search books by subject/topic.

        Args:
            subject: Subject name
            limit: Maximum results

        Returns:
            Search results
        """
        fields = [
            "key",
            "title",
            "author_name",
            "first_publish_year",
            "isbn",
            "subject",
            "publisher",
            "language",
            "number_of_pages_median",
            "cover_i",
            "has_fulltext",
        ]
        return self.search_books(query=f"subject:{subject}", limit=limit, fields=fields)

    def search_by_author(self, author: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search books by author name.

        Args:
            author: Author name
            limit: Maximum results

        Returns:
            Search results
        """
        fields = [
            "key",
            "title",
            "author_name",
            "first_publish_year",
            "isbn",
            "subject",
            "publisher",
            "language",
            "number_of_pages_median",
            "cover_i",
            "has_fulltext",
        ]
        return self.search_books(query=f"author:{author}", limit=limit, fields=fields)

    def get_subjects_for_work(self, work_id: str) -> List[str]:
        """Get list of subjects for a work."""
        details = self.get_work_details(work_id)
        return details.get("subjects", [])

    def extract_keywords_from_text(
        self, text: str, max_keywords: int = 10
    ) -> List[str]:
        """
        Extract meaningful keywords from text for book search.

        Args:
            text: Input text to analyze
            max_keywords: Maximum number of keywords to extract

        Returns:
            List of keywords
        """
        # Remove punctuation and split
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())

        # Common stop words to exclude
        stop_words = {
            "that",
            "this",
            "with",
            "from",
            "have",
            "been",
            "were",
            "will",
            "would",
            "could",
            "should",
            "about",
            "which",
            "their",
            "there",
            "where",
            "these",
            "those",
            "when",
            "what",
            "who",
            "how",
            "why",
            "some",
            "such",
            "into",
            "than",
            "then",
            "them",
            "they",
            "your",
        }

        # Filter and count
        keyword_counts = {}
        for word in words:
            if word not in stop_words and len(word) > 3:
                keyword_counts[word] = keyword_counts.get(word, 0) + 1

        # Sort by frequency and return top keywords
        sorted_keywords = sorted(
            keyword_counts.items(), key=lambda x: x[1], reverse=True
        )

        return [kw[0] for kw in sorted_keywords[:max_keywords]]

    def recommend_books_for_text(
        self,
        text: str,
        limit: int = 5,
        prefer_diverse_authors: bool = True,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze text and recommend relevant books.

        Args:
            text: Text to analyze
            limit: Number of recommendations
            prefer_diverse_authors: Try to get books from different authors
            language: Optional language code to filter results (e.g., 'chi', 'eng', 'jpn')

        Returns:
            Dictionary with recommendations and metadata
        """
        # Extract keywords
        keywords = self.extract_keywords_from_text(text, max_keywords=5)

        if not keywords:
            return {
                "recommendations": [],
                "keywords": [],
                "message": "Could not extract meaningful keywords from text",
            }

        # Search using top keywords with explicit fields
        search_query = " ".join(keywords[:3])
        fields = [
            "key",
            "title",
            "author_name",
            "first_publish_year",
            "isbn",
            "subject",
            "publisher",
            "language",
            "number_of_pages_median",
            "cover_i",
            "has_fulltext",
        ]
        results = self.search_books(
            search_query, limit=limit * 3, fields=fields, language=language
        )

        recommendations = []
        seen_authors = set()

        for doc in results.get("docs", []):
            authors = doc.get("author_name", [])
            author_key = tuple(authors) if authors else ("unknown",)

            if prefer_diverse_authors:
                # Prioritize books from different authors
                if len(recommendations) < limit:
                    recommendations.append(doc)
                    seen_authors.add(author_key)
                elif (
                    author_key not in seen_authors and len(recommendations) < limit * 2
                ):
                    recommendations.append(doc)
                    seen_authors.add(author_key)
            else:
                recommendations.append(doc)

            if len(recommendations) >= limit:
                break

        return {
            "text_length": len(text),
            "keywords": keywords,
            "num_found": results.get("numFound", 0),
            "recommendations": recommendations[:limit],
        }

    def format_book_summary(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a book document into a clean summary.

        Args:
            doc: Book document from search results

        Returns:
            Formatted book summary
        """
        return {
            "title": doc.get("title", "Unknown Title"),
            "authors": doc.get("author_name", ["Unknown Author"]),
            "first_publish_year": doc.get("first_publish_year"),
            "isbn": doc.get("isbn", [None])[0] if doc.get("isbn") else None,
            "subjects": doc.get("subject", [])[:10],
            "publishers": doc.get("publisher", [])[:5],
            "language": doc.get("language", []),
            "number_of_pages": doc.get("number_of_pages_median"),
            "openlibrary_key": doc.get("key"),
            "cover_id": doc.get("cover_i"),
            "has_fulltext": doc.get("has_fulltext", False),
        }

    def get_cover_url(self, cover_id: int, size: str = "M") -> str:
        """
        Get cover image URL.

        Args:
            cover_id: Cover ID from book data
            size: Size code (S=small, M=medium, L=large)

        Returns:
            Cover image URL
        """
        return f"{OPENLIBRARY_COVER_API}/id/{cover_id}-{size}.jpg"

    def analyze_text_difficulty_with_ai(
        self, text: str, language: str = "chi"
    ) -> Dict[str, Any]:
        """
        Analyze text difficulty using AI to determine HSK level for Chinese text.

        Args:
            text: Text to analyze
            language: Language code (chi, eng, jpn, etc.)

        Returns:
            Dictionary with difficulty metrics including HSK level
        """
        from .ollama_client import OllamaClient
        import json

        ollama = OllamaClient()

        if language == "chi" and ollama.check_connection():
            # Use AI to determine HSK level
            prompt = f"""Analyze the following Chinese text and determine its HSK level (1-6).

Text: {text}

Provide your analysis as JSON with these fields:
- hsk_level: integer from 1 to 6 (1=beginner, 6=advanced)
- difficulty_level: string ("beginner", "intermediate", "advanced", or "native")
- complexity_score: float from 0-100
- vocabulary_complexity: string describing the vocabulary level
- grammar_complexity: string describing the grammar level
- estimated_study_hours: integer (approximate hours needed to read this level)

Rules:
- HSK 1-2: beginner (200-600 hours)
- HSK 3-4: intermediate (600-1200 hours) 
- HSK 5: advanced (1200-2500 hours)
- HSK 6+: native (2500+ hours)

Respond ONLY with valid JSON, no other text."""

            response = ollama.call_ollama(
                prompt, schema_name="translate", stage_label="HSK Analysis"
            )

            if response:
                cleaned = ollama.clean_thinking(response)
                parsed, success = ollama.safe_json_parse(cleaned)

                if success and "hsk_level" in parsed:
                    return {
                        "hsk_level": parsed.get("hsk_level", 3),
                        "difficulty_level": parsed.get(
                            "difficulty_level", "intermediate"
                        ),
                        "complexity_score": float(parsed.get("complexity_score", 50.0)),
                        "vocabulary_complexity": parsed.get(
                            "vocabulary_complexity", "Unknown"
                        ),
                        "grammar_complexity": parsed.get(
                            "grammar_complexity", "Unknown"
                        ),
                        "estimated_study_hours": parsed.get(
                            "estimated_study_hours", 600
                        ),
                        "character_count": len(
                            [c for c in text if "\u4e00" <= c <= "\u9fff"]
                        ),
                        "unique_characters": len(
                            set(c for c in text if "\u4e00" <= c <= "\u9fff")
                        ),
                        "word_count": len(
                            [c for c in text if "\u4e00" <= c <= "\u9fff"]
                        ),
                        "avg_word_length": 1.0,
                    }

        # Fallback to simple analysis
        return self._simple_difficulty_analysis(text, language)

    def _simple_difficulty_analysis(
        self, text: str, language: str = "chi"
    ) -> Dict[str, Any]:
        """
        Simple difficulty analysis without AI (fallback method).
        """
        import unicodedata

        # Remove punctuation and whitespace for clean analysis
        characters = [
            c for c in text if c.strip() and not unicodedata.category(c).startswith("P")
        ]
        character_count = len(characters)
        unique_characters = len(set(characters))

        # Detect if text is primarily CJK (Chinese/Japanese/Korean)
        cjk_count = sum(
            1
            for c in characters
            if "\u4e00" <= c <= "\u9fff"
            or "\u3040" <= c <= "\u309f"
            or "\u30a0" <= c <= "\u30ff"
            or "\uac00" <= c <= "\ud7af"
        )
        is_cjk = cjk_count > character_count * 0.5

        if is_cjk:
            # For CJK: use character count as proxy for words
            word_count = character_count
            avg_word_length = 1.0  # Each character is roughly one concept

            # CJK complexity based on character variety and text length
            unique_ratio = (
                unique_characters / character_count if character_count > 0 else 0
            )

            # Complexity score for CJK (0-100)
            complexity_score = (
                (unique_ratio * 40)  # Vocabulary diversity
                + (min(character_count / 50, 1.0) * 30)  # Text length (cap at 50 chars)
                + (min(unique_characters / 30, 1.0) * 30)  # Unique character count
            )

            # CJK difficulty thresholds
            if character_count < 10:
                difficulty_level = "beginner"
            elif character_count < 30:
                difficulty_level = "intermediate"
            elif character_count < 60:
                difficulty_level = "advanced"
            else:
                difficulty_level = "native"

        else:
            # For non-CJK: use space-separated words
            words = text.split()
            word_count = len(words)
            avg_word_length = (
                sum(len(w) for w in words) / word_count if word_count > 0 else 0
            )

            unique_ratio = (
                unique_characters / character_count if character_count > 0 else 0
            )

            # Complexity score for alphabetic languages
            complexity_score = (
                (unique_ratio * 25)  # Character variety
                + (min(avg_word_length / 10, 1.0) * 25)  # Longer words = harder
                + (min(word_count / 50, 1.0) * 25)  # More words = harder
                + (min(character_count / 200, 1.0) * 25)  # Text length
            )

            # Alphabetic language thresholds
            if complexity_score < 30:
                difficulty_level = "beginner"
            elif complexity_score < 50:
                difficulty_level = "intermediate"
            elif complexity_score < 70:
                difficulty_level = "advanced"
            else:
                difficulty_level = "native"

        return {
            "character_count": character_count,
            "unique_characters": unique_characters,
            "word_count": word_count,
            "avg_word_length": round(avg_word_length, 2),
            "complexity_score": round(complexity_score, 2),
            "difficulty_level": difficulty_level,
            "hsk_level": None,
            "vocabulary_complexity": "Not analyzed",
            "grammar_complexity": "Not analyzed",
            "estimated_study_hours": None,
        }

    def analyze_text_difficulty_with_ai(
        self, text: str, language: str = "chi"
    ) -> Dict[str, Any]:
        """
        Analyze text difficulty using AI to determine HSK level for Chinese text.

        Args:
            text: Text to analyze
            language: Language code (chi, eng, jpn, etc.)

        Returns:
            Dictionary with difficulty metrics including HSK level
        """
        from .ollama_client import OllamaClient
        import json

        ollama = OllamaClient()

        if language == "chi" and ollama.check_connection():
            # Use AI to determine HSK level
            prompt = f"""Analyze the following Chinese text and determine its HSK level (1-6).

Text: {text}

Provide your analysis as JSON with these fields:
- hsk_level: integer from 1 to 6 (1=beginner, 6=advanced)
- difficulty_level: string ("beginner", "intermediate", "advanced", or "native")
- complexity_score: float from 0-100
- vocabulary_complexity: string describing the vocabulary level
- grammar_complexity: string describing the grammar level
- estimated_study_hours: integer (approximate hours needed to read this level)

Rules:
- HSK 1-2: beginner (200-600 hours total study time)
- HSK 3-4: intermediate (600-1200 hours total study time) 
- HSK 5: advanced (1200-2500 hours total study time)
- HSK 6+: native (2500+ hours total study time)

Respond ONLY with valid JSON, no other text."""

            response = ollama.call_ollama(
                prompt, schema_name="translate", stage_label="HSK Analysis"
            )

            if response:
                cleaned = ollama.clean_thinking(response)
                parsed, success = ollama.safe_json_parse(cleaned)

                if success and "hsk_level" in parsed:
                    chinese_chars = [c for c in text if "\u4e00" <= c <= "\u9fff"]
                    return {
                        "hsk_level": parsed.get("hsk_level", 3),
                        "difficulty_level": parsed.get(
                            "difficulty_level", "intermediate"
                        ),
                        "complexity_score": float(parsed.get("complexity_score", 50.0)),
                        "vocabulary_complexity": parsed.get(
                            "vocabulary_complexity", "Unknown"
                        ),
                        "grammar_complexity": parsed.get(
                            "grammar_complexity", "Unknown"
                        ),
                        "estimated_study_hours": parsed.get(
                            "estimated_study_hours", 600
                        ),
                        "character_count": len(chinese_chars),
                        "unique_characters": len(set(chinese_chars)),
                        "word_count": len(chinese_chars),
                        "avg_word_length": 1.0,
                    }

        # Fallback to simple analysis if AI fails or not Chinese
        import unicodedata

        characters = [
            c for c in text if c.strip() and not unicodedata.category(c).startswith("P")
        ]
        character_count = len(characters)

        cjk_count = sum(
            1
            for c in characters
            if "\u4e00" <= c <= "\u9fff"
            or "\u3040" <= c <= "\u309f"
            or "\u30a0" <= c <= "\u30ff"
            or "\uac00" <= c <= "\ud7af"
        )
        is_cjk = cjk_count > character_count * 0.5

        if is_cjk:
            word_count = character_count
            avg_word_length = 1.0
            unique_characters = len(set(characters))
            unique_ratio = (
                unique_characters / character_count if character_count > 0 else 0
            )

            complexity_score = (
                (unique_ratio * 40)
                + (min(character_count / 50, 1.0) * 30)
                + (min(unique_characters / 30, 1.0) * 30)
            )

            if character_count < 10:
                difficulty_level = "beginner"
            elif character_count < 30:
                difficulty_level = "intermediate"
            elif character_count < 60:
                difficulty_level = "advanced"
            else:
                difficulty_level = "native"
        else:
            words = text.split()
            word_count = len(words)
            unique_characters = len(set(characters))
            avg_word_length = (
                sum(len(w) for w in words) / word_count if word_count > 0 else 0
            )
            unique_ratio = (
                unique_characters / character_count if character_count > 0 else 0
            )

            complexity_score = (
                (unique_ratio * 25)
                + (min(avg_word_length / 10, 1.0) * 25)
                + (min(word_count / 50, 1.0) * 25)
                + (min(character_count / 200, 1.0) * 25)
            )

            if complexity_score < 30:
                difficulty_level = "beginner"
            elif complexity_score < 50:
                difficulty_level = "intermediate"
            elif complexity_score < 70:
                difficulty_level = "advanced"
            else:
                difficulty_level = "native"

        return {
            "character_count": character_count,
            "unique_characters": unique_characters,
            "word_count": word_count,
            "avg_word_length": round(avg_word_length, 2),
            "complexity_score": round(complexity_score, 2),
            "difficulty_level": difficulty_level,
            "hsk_level": None,
            "vocabulary_complexity": "Not analyzed with AI",
            "grammar_complexity": "Not analyzed with AI",
            "estimated_study_hours": None,
        }

    def analyze_text_difficulty(
        self, text: str, language: str = "chi"
    ) -> Dict[str, Any]:
        """
        Analyze text difficulty. Uses AI for Chinese text, simple analysis for others.
        """
        return self.analyze_text_difficulty_with_ai(text, language)

    def find_texts_by_difficulty(
        self, target_metrics: Dict[str, Any], language: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find texts with similar difficulty level using OpenLibrary and HSK-based queries.

        Args:
            target_metrics: Target difficulty metrics to match (includes hsk_level if available)
            language: Language code
            limit: Number of results

        Returns:
            List of books with similar difficulty
        """
        difficulty_level = target_metrics["difficulty_level"]
        hsk_level = target_metrics.get("hsk_level")

        # Enhanced search queries based on HSK level for Chinese - focus on actual literature
        if language == "chi" and hsk_level:
            if hsk_level <= 2:
                queries = [
                    "children chinese story",
                    "chinese fairy tale",
                    "simple chinese fiction",
                ]
            elif hsk_level <= 4:
                queries = [
                    "chinese young adult",
                    "contemporary chinese fiction",
                    "chinese short story",
                ]
            elif hsk_level == 5:
                queries = [
                    "chinese literature",
                    "modern chinese novel",
                    "chinese fiction",
                ]
            else:
                queries = [
                    "chinese classics",
                    "contemporary chinese literature",
                    "chinese novel",
                ]
        else:
            # Default search queries based on difficulty level
            search_queries = {
                "beginner": ["children stories", "fairy tales"],
                "intermediate": ["young adult fiction", "short stories"],
                "advanced": ["literature", "novel"],
                "native": ["classic literature", "contemporary fiction"],
            }
            queries = search_queries.get(difficulty_level, ["literature"])

        results = []

        # Keywords to filter out test prep books
        exclude_keywords = [
            "hsk",
            "test",
            "exam",
            "mock",
            "practice",
            "workbook",
            "textbook",
            "course",
            "lesson",
            "exercise",
            "grammar",
            "vocabulary",
            "flashcard",
            "study guide",
            "prep",
        ]

        fields = [
            "key",
            "title",
            "author_name",
            "first_publish_year",
            "isbn",
            "subject",
            "publisher",
            "language",
            "number_of_pages_median",
            "cover_i",
            "has_fulltext",
        ]

        for query in queries[:3]:  # Use first 3 queries
            search_results = self.search_books(
                query=query, limit=limit * 2, language=language, fields=fields
            )

            # Filter out HSK/test prep books
            for doc in search_results.get("docs", []):
                title_lower = doc.get("title", "").lower()
                subjects_lower = " ".join(doc.get("subject", [])).lower()

                # Skip if title or subjects contain excluded keywords
                if any(
                    keyword in title_lower or keyword in subjects_lower
                    for keyword in exclude_keywords
                ):
                    continue

                results.append(doc)
                if len(results) >= limit:
                    break

            if len(results) >= limit:
                break

        return results[:limit]
