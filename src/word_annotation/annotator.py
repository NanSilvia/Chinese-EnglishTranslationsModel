"""
MandarinSpot Annotator - Python wrapper for Chinese text annotation

This module provides a simple API to annotate Chinese characters with their
pronunciation and definitions, without any DOM manipulation.

Usage:
    from annotator import MandarinAnnotator

    annotator = MandarinAnnotator()
    annotations = annotator.annotate("你好")
    for ann in annotations:
        print(f"{ann['character']}: {ann['pinyin']}")
"""

import hashlib
import json
import re
from typing import List, Dict, Optional, Tuple, Callable, Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError


class MandarinAnnotator:
    """Chinese text annotator with pronunciation and definition lookup."""

    def __init__(self, api_url: str = "https://api.mandarinspot.com"):
        """
        Initialize the annotator.

        Args:
            api_url: Base URL for the MandarinSpot API
        """
        self.api_url = api_url
        self.dictionary: Dict[str, Any] = {}
        self.cjk_start = 0x4E00  # 19968
        self.cjk_end = 0x9FFF  # 40879

    def is_cjk_character(self, ch: str) -> bool:
        """
        Check if a character is CJK (Chinese, Japanese, Korean).

        Args:
            ch: Single character to check

        Returns:
            True if character is CJK
        """
        if not ch:
            return False
        char_code = ord(ch)
        return self.cjk_start <= char_code <= self.cjk_end

    def find_cjk_segments(self, text: str) -> List[Tuple[bool, int, int]]:
        """
        Find all continuous CJK character segments in text.

        Args:
            text: Input text

        Returns:
            List of [is_cjk, start_index, end_index] segments
        """
        segments = []
        i = 0

        while i < len(text):
            is_cjk = self.is_cjk_character(text[i])
            j = i + 1

            # Continue while characters match CJK status
            while j < len(text) and self.is_cjk_character(text[j]) == is_cjk:
                j += 1

            segments.append((is_cjk, i, j))
            i = j

        return segments

    def extract_cjk_characters(self, text: str) -> List[str]:
        """
        Extract all CJK characters from text.

        Args:
            text: Input text

        Returns:
            List of CJK characters
        """
        return [ch for ch in text if self.is_cjk_character(ch)]

    def encode_base32(self, arr: List[str]) -> List[str]:
        """
        Encode array to base-32 string (matching JavaScript Number.toString(32)).

        Args:
            arr: Array of strings

        Returns:
            Array of base-32 encoded strings
        """

        def to_base32(num):
            """Convert number to base-32 string like JavaScript."""
            if num == 0:
                return "0"
            chars = "0123456789abcdefghijklmnopqrstuvwxyz"
            result = ""
            is_negative = num < 0
            num = abs(num)
            while num > 0:
                result = chars[num % 32] + result
                num //= 32
            return ("-" + result) if is_negative else result

        result = []
        for s in arr:
            encoded = ""
            for ch in s:
                # Convert to base-32 like JavaScript: (charCode - 8192).toString(32)
                char_code = ord(ch)
                value = char_code - 8192
                encoded += to_base32(value)
            result.append(encoded)
        return result
        return result

    def encode_utf8(self, arr: List[str]) -> List[str]:
        """
        Encode array to UTF-8 compatible format.

        Args:
            arr: Array of strings

        Returns:
            Array of UTF-8 encoded strings
        """
        result = []
        for s in arr:
            encoded = ""
            for ch in s:
                char_code = ord(ch)
                encoded += chr(224 | (15 & (char_code >> 12)))
                encoded += chr(128 | (63 & (char_code >> 6)))
                encoded += chr(128 | (63 & char_code))
            result.append(encoded)
        return result

    def sha1_hash(self, msg: str) -> str:
        """
        Generate SHA-1 hash of message.

        Args:
            msg: Message to hash

        Returns:
            SHA-1 hash in hex format
        """
        return hashlib.sha1(msg.encode("utf-8")).hexdigest()

    def http_request(
        self,
        method: str,
        url: str,
        params: Dict[str, str],
        callback: Optional[Callable] = None,
    ) -> Optional[Dict]:
        """
        Make HTTP request.

        Args:
            method: HTTP method (GET or POST)
            url: Request URL
            params: Parameters dictionary
            callback: Optional callback function(error, response)

        Returns:
            Response data if no callback provided
        """
        try:
            param_str = urlencode(params)

            if method == "GET":
                final_url = f"{url}?{param_str}" if param_str else url
                req = Request(final_url, method="GET")
            else:  # POST
                final_url = url
                req = Request(final_url, data=param_str.encode("utf-8"), method="POST")
                req.add_header("Content-Type", "application/x-www-form-urlencoded")

            with urlopen(req, timeout=10) as response:
                response_data = json.loads(response.read().decode("utf-8"))

            if callback:
                callback(None, response_data)
            return response_data

        except URLError as e:
            error_msg = str(e)
            if callback:
                callback(error_msg, None)
            else:
                raise

    def get_definitions(
        self,
        characters: List[str],
        phonetic_type: str = "pinyin",
        callback: Optional[Callable] = None,
    ) -> Optional[Dict]:
        """
        Get definitions for CJK characters.

        Args:
            characters: List of CJK characters
            phonetic_type: Type of phonetic (pinyin, cantonese, etc)
            callback: Optional callback function(error, definitions)

        Returns:
            Definitions if no callback provided
        """
        # Send raw characters, not base32 encoded
        char_str = "".join(characters)
        hash_input = ",".join(self.encode_utf8(characters)) + phonetic_type
        cache_hash = self.sha1_hash(hash_input)

        # If callback provided, use async
        if callback:

            def try_cache():
                try:
                    cache_url = f"{self.api_url}/cache/{cache_hash}"
                    response = self.http_request("GET", cache_url, {})
                    if response:
                        callback(None, response)
                        return
                except:
                    pass

                # Fetch from API if cache miss
                def_url = f"{self.api_url}/getdefs"
                params = {"str": char_str, "phs": phonetic_type}
                self.http_request("POST", def_url, params, callback)

            try_cache()
            return None

        # Synchronous mode
        try:
            cache_url = f"{self.api_url}/cache/{cache_hash}"
            response = self.http_request("GET", cache_url, {})
            if response:
                return response
        except:
            pass

        # Fetch from API
        def_url = f"{self.api_url}/getdefs"
        params = {"str": char_str, "phs": phonetic_type}
        return self.http_request("POST", def_url, params)

    def format_annotations(
        self, def_data: Dict, text: str, cjk_chars: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Format definition data into structured annotations.

        Args:
            def_data: Definition data from API
            text: Original text
            cjk_chars: CJK characters found

        Returns:
            List of annotation dictionaries
        """
        annotations = []
        defs = def_data.get("defs", {})

        for char in cjk_chars:
            if char in defs:
                def_info = defs[char]
                annotations.append(
                    {
                        "character": char,
                        "index": text.find(char),
                        "pinyin": def_info[0] if len(def_info) > 0 else [],
                        "simplified": def_info[1] if len(def_info) > 1 else [],
                        "traditional": def_info[2] if len(def_info) > 2 else char,
                        "definitions": def_info[1] if len(def_info) > 1 else [],
                    }
                )

        return annotations

    def group_annotations_to_words(
        self, text: str, annotations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Group individual character annotations into continuous word segments.

        Args:
            text: Original text
            annotations: List of character-level annotations

        Returns:
            List of word-level annotations with consecutive characters grouped
        """
        if not annotations:
            return []

        # Get CJK segments to identify word boundaries
        segments = self.find_cjk_segments(text)
        words = []

        # Build a map of character index to annotation
        ann_map = {text.find(ann["character"]): ann for ann in annotations}

        # Process each segment
        for is_cjk, start, end in segments:
            if is_cjk:
                # This is a CJK segment - group characters into a word
                word_text = text[start:end]
                word_annotations = []

                for i, char in enumerate(word_text):
                    for ann in annotations:
                        if ann["character"] == char:
                            word_annotations.append(ann)
                            break

                if word_annotations:
                    # Combine multiple annotations for the word
                    combined = {
                        "word": word_text,
                        "start_index": start,
                        "end_index": end,
                        "length": len(word_text),
                        "characters": [ann["character"] for ann in word_annotations],
                        "pinyin": [
                            (ann["pinyin"][0] if ann["pinyin"] else ann["character"])
                            for ann in word_annotations
                        ],
                        "definitions": [ann["definitions"] for ann in word_annotations],
                        "details": word_annotations,
                    }
                    words.append(combined)

        return words

    def create_word_annotations(
        self, text: str, cjk_chars: List[str], def_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Create word-level annotations using MandarinSpot's segmentation data.
        The seg array contains base-32 encoded character widths for each word.

        Args:
            text: Original text
            cjk_chars: List of CJK characters found
            def_data: Definition data from API with segmentation info

        Returns:
            List of word-level annotation dictionaries
        """
        defs = def_data.get("defs", {})
        seg_data = def_data.get("seg", [])

        words = []
        char_index = 0

        # Process each segmentation string
        # Each string in seg_data contains base-32 encoded character widths for that segment
        for seg_str in seg_data:
            if not seg_str:
                continue

            # Parse each character in the segmentation string as a word width
            for seg_char in seg_str:
                try:
                    # Decode base-32: '1' = 1-char word, '2' = 2-char word, etc
                    char_width = int(seg_char, 32)
                except ValueError:
                    # Fallback to 1 if parsing fails
                    char_width = 1

                # Collect characters for this word
                word_chars = []
                for _ in range(char_width):
                    if char_index < len(cjk_chars):
                        word_chars.append(cjk_chars[char_index])
                        char_index += 1

                # Create word annotation
                if word_chars:
                    word_text = "".join(word_chars)

                    # Check if this word has a direct entry in defs
                    if word_text in defs:
                        # Multi-character word found in defs
                        def_info = defs[word_text]
                        pinyin = def_info[0] if len(def_info) > 0 else []
                        definitions = def_info[1] if len(def_info) > 1 else []
                        traditional = def_info[2] if len(def_info) > 2 else word_text

                        pinyin_str = " ".join(pinyin) if pinyin else ""
                        definitions_list = definitions if definitions else []

                        char_details = [
                            {
                                "character": word_text,
                                "pinyin": pinyin,
                                "definitions": definitions,
                                "traditional": traditional,
                            }
                        ]
                    else:
                        # Fall back to individual character lookup
                        pinyin_list = []
                        definitions_list = []
                        char_details = []

                        for char in word_chars:
                            if char in defs:
                                def_info = defs[char]
                                pinyin = def_info[0] if len(def_info) > 0 else []
                                definitions = def_info[1] if len(def_info) > 1 else []
                                traditional = def_info[2] if len(def_info) > 2 else char

                                # Use first pronunciation only
                                pinyin_list.append(pinyin[0] if pinyin else char)
                                # Collect all definitions
                                if definitions:
                                    definitions_list.extend(definitions)
                                char_details.append(
                                    {
                                        "character": char,
                                        "pinyin": pinyin,
                                        "definitions": definitions,
                                        "traditional": traditional,
                                    }
                                )

                        pinyin_str = " ".join(pinyin_list)

                    word_annotation = {
                        "word": word_text,
                        "pinyin": pinyin_str,
                        "pinyin_list": (
                            [pinyin_str]
                            if word_text in defs
                            else [
                                d["pinyin"][0] if d.get("pinyin") else ""
                                for d in char_details
                            ]
                        ),
                        "definitions": (
                            definitions_list[:2] if definitions_list else []
                        ),
                        "definitions_full": definitions_list,
                        "character_count": len(word_chars),
                        "characters": word_chars,
                        "details": char_details,
                    }
                    words.append(word_annotation)

        return words

    def annotate(
        self,
        text: str,
        phonetic_type: str = "pinyin",
        callback: Optional[Callable] = None,
        as_words: bool = False,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Annotate Chinese text.

        Args:
            text: Chinese text to annotate
            phonetic_type: Type of phonetic (pinyin, cantonese, etc)
            callback: Optional callback function(error, annotations)
            as_words: If True, use word-level segmentation from API; if False, return individual characters

        Returns:
            List of annotations if no callback provided
        """
        cjk_chars = self.extract_cjk_characters(text)

        if not cjk_chars:
            if callback:
                callback(None, [])
            return []

        # If callback is provided, use async mode
        if callback:

            def on_definitions(err, data):
                if err:
                    callback(err, None)
                else:
                    if as_words:
                        annotations = self.create_word_annotations(
                            text, cjk_chars, data
                        )
                    else:
                        annotations = self.format_annotations(data, text, cjk_chars)
                    callback(None, annotations)

            self.get_definitions(cjk_chars, phonetic_type, on_definitions)
            return None

        # Otherwise, use synchronous mode
        try:
            data = self.get_definitions(cjk_chars, phonetic_type)
            if data:
                if as_words:
                    annotations = self.create_word_annotations(text, cjk_chars, data)
                else:
                    annotations = self.format_annotations(data, text, cjk_chars)
                return annotations
            return []
        except Exception as e:
            raise e


# Example usage
if __name__ == "__main__":
    annotator = MandarinAnnotator()

    # Synchronous example
    try:
        annotations = annotator.annotate("你好", phonetic_type="pinyin")
        if annotations:
            for ann in annotations:
                print(f"{ann['character']}: {ann['pinyin']}")
    except Exception as e:
        print(f"Error: {e}")

    # Asynchronous example
    def handle_result(err, annotations):
        if err:
            print(f"Error: {err}")
        else:
            print("Annotations:", annotations)

    # annotator.annotate("世界", callback=handle_result)
