"""
Dictionary utilities for BDIC dictionary loading and Chinese term extraction.
"""

import re
import difflib
from typing import List, Dict, Any

from .config import DICTIONARY_BDIC_PATH

try:
    from pypinyin import lazy_pinyin
except ImportError:
    lazy_pinyin = None

# Dictionary pattern for Chinese terms (2-6 characters)
CHINESE_TERM_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,6}")


def _load_bdic_dictionary(path: str, max_words: int = 120000) -> List[str]:
    """Load BDIC dictionary file and extract English words."""
    try:
        with open(path, "rb") as f:
            raw_bytes = f.read()
        decoded = raw_bytes.decode("latin-1", errors="ignore")
        tokens = re.findall(r"[A-Za-z][A-Za-z\-']{1,29}", decoded)
        normalized = {token.lower() for token in tokens if len(token) >= 2}
        words = sorted(normalized)
        if max_words:
            words = words[:max_words]
        return words
    except Exception:
        return []


# Load dictionary words at module initialization
DICTIONARY_WORDS = _load_bdic_dictionary(DICTIONARY_BDIC_PATH)


def romanize_chinese(term: str) -> str:
    """Convert Chinese characters to pinyin romanization."""
    if not term:
        return ""
    if lazy_pinyin:
        return "".join(lazy_pinyin(term))
    return term


def extract_chinese_terms(text: str, max_terms: int = 8) -> List[str]:
    """Extract Chinese terms from text using pattern matching."""
    if not isinstance(text, str):
        return []
    terms = CHINESE_TERM_PATTERN.findall(text)
    unique_terms = []
    for term in terms:
        if term not in unique_terms:
            unique_terms.append(term)
        if len(unique_terms) >= max_terms:
            break
    return unique_terms


def lookup_dictionary_entries(text: str, max_entries: int = 5) -> List[Dict[str, Any]]:
    """
    Look up Chinese terms in BDIC dictionary and find English word suggestions.
    Matches the exact process from the notebook.
    """
    if not DICTIONARY_WORDS:
        return []

    entries = []
    for term in extract_chinese_terms(text, max_entries * 2):
        romanized = romanize_chinese(term)
        if not romanized:
            continue

        # Find close matches in dictionary using difflib
        suggestions = difflib.get_close_matches(
            romanized.lower(), DICTIONARY_WORDS, n=3, cutoff=0.6
        )

        if suggestions:
            entries.append(
                {
                    "source_term": term,
                    "romanized": romanized,
                    "suggestions": suggestions,
                }
            )

        if len(entries) >= max_entries:
            break

    return entries


def format_dictionary_prompt(entries: List[Dict[str, Any]]) -> str:
    """Format dictionary entries into a prompt text."""
    if not entries:
        return "No dictionary matches were found for this text."

    lines = []
    for entry in entries:
        suggestion_text = ", ".join(entry["suggestions"])
        lines.append(
            f"{entry['source_term']} ({entry['romanized']}): possible English matches -> {suggestion_text}"
        )
    return "\n".join(lines)
