"""
Translation service module with Qwen/Ollama integration.
Handles model inference and response processing with dictionary enrichment.
"""

import json
import time
import re
import requests
import difflib
from typing import Optional, Dict, Any, Tuple, List

try:
    from json_repair import repair_json
except ImportError:
    repair_json = None

from .config import (
    OLLAMA_API_BASE,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    OLLAMA_STREAMING,
    DEFAULT_AGENT,
    DICTIONARY_BDIC_PATH,
)
from .schemas import PromptingSchemaRegistry

# Dictionary pattern for Chinese terms (2-6 characters)
CHINESE_TERM_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,6}")

try:
    from pypinyin import lazy_pinyin
except ImportError:
    lazy_pinyin = None


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

# Translation system prompts (from notebook)
SYSTEM_PROMPT = """You are an expert translator and language analyst. You will receive text in a JSON format that must be translated and explained. Your task is to:

1. Produce a complete, fluent translation of the entire input text.
2. Identify and explain:
   - The most challenging grammatical structures (e.g. verb tenses, clause structures, agreement, word order, subordination, complex sentences), and
   - The most challenging or hard-to-understand phrases/expressions (e.g. idioms, collocations, ambiguous phrases, fixed expressions).

The input JSON format is:
{
  "input_text": "<text_here>",
  "initial_translation": "<optional_translation_here>"
}

"initial_translation" will contain the first-pass translation that you previously produced. Use it as your starting point, refine it if needed, and then generate the explanations requested below.

You must respond with a single JSON object in the following format:
{
  "translated_text": "<translated_text>",
  "explainations_list": [
    ["<challenging_part_1>", "<explanation_1>"],
    ["<challenging_part_2>", "<explanation_2>"]
  ]
}

Where:
- "translated_text" is the complete, fluent translation of the entire "input_text".
- "explainations_list" is a list of tuples (2-element arrays):
  - The first element is a challenging part taken directly from "input_text". This can be either:
    - a grammatical structure (clause, verb group, sentence fragment, etc.), or
    - a phrase/expression that is hard to understand or translate literally.
  - The second element is a clear explanation (in the target language) that:
    - for grammatical structures: describes the relevant grammar (e.g. tense, aspect, mood, syntax, agreement, clause type) and how it affects meaning;
    - for phrases/expressions: explains the intended meaning, why it is challenging (idiomatic, ambiguous, non-literal, etc.), and how that meaning is captured in the translation.

Important rules:
- Cover both types of difficulties: grammar AND challenging phrases/expressions whenever they are present.
- Focus explanations on what makes each selected part non-trivial to understand or translate.
- Respond with only the valid JSON and only the valid JSON.
- Do not output any other strings, comments, or messages outside the JSON.
- Ensure the JSON is syntactically valid (double quotes for all keys and string values, no trailing commas)."""

TRANSLATION_ONLY_SYSTEM_PROMPT = """You are an expert translator. You will receive a JSON payload of the form {"input_text": "<text_here>"}. Translate the entire text fluently and respond ONLY with valid JSON:
{
  "translated_text": "<translated_text>"
}
Do not include any other keys, explanations, or commentary. Ensure the JSON is valid and double-quoted."""

TRANSLATION_ONLY_FALLBACK_PROMPT = """You are an expert translator. Translate the user's message into fluent English. Respond with the translated sentence only-no JSON, commentary, or metadata."""

TRANSLATION_ONLY_FALLBACK_PROMPT = """You are an expert translator. Translate the user's message into fluent English. Respond with the translated sentence only-no JSON, commentary, or metadata."""


class TranslationService:
    """Handles translation operations using configured agent."""

    def __init__(self):
        self.default_agent = DEFAULT_AGENT
        self.ollama_connected = None

    def _romanize_chinese(self, term: str) -> str:
        """Convert Chinese characters to pinyin romanization."""
        if not term:
            return ""
        if lazy_pinyin:
            return "".join(lazy_pinyin(term))
        return term

    def _extract_chinese_terms(self, text: str, max_terms: int = 8) -> List[str]:
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

    def _lookup_dictionary_entries(
        self, text: str, max_entries: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Look up Chinese terms in BDIC dictionary and find English word suggestions.
        Matches the exact process from the notebook.
        """
        if not DICTIONARY_WORDS:
            return []

        entries = []
        for term in self._extract_chinese_terms(text, max_entries * 2):
            romanized = self._romanize_chinese(term)
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

    def _format_dictionary_prompt(self, entries: List[Dict[str, Any]]) -> str:
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

    def _check_ollama_connection(self) -> bool:
        """Check if Ollama is available."""
        if self.ollama_connected is not None:
            return self.ollama_connected

        try:
            response = requests.get(f"{OLLAMA_API_BASE}/api/tags", timeout=5)
            if response.status_code == 200:
                self.ollama_connected = True
                return True
        except Exception as e:
            print(f"Ollama connection failed: {e}")

        self.ollama_connected = False
        return False

    def _clean_thinking(self, text: str) -> str:
        """Remove thinking tags and markdown code blocks from response."""
        if not isinstance(text, str):
            return text
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
        text = re.sub(r"<think>.*$", "", text, flags=re.S)
        # Remove markdown code block markers (```json or ```)
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()

    def _safe_json_parse(self, text: str) -> Tuple[Dict[str, Any], bool]:
        """
        Safely parse JSON with repair fallback.

        Returns:
            Tuple of (parsed_dict, success_bool)
            - If parsing succeeds: (dict, True)
            - If parsing fails: ({}, False)
        """
        if not isinstance(text, str) or not text:
            return {}, False

        # First, try standard JSON parsing
        try:
            return json.loads(text), True
        except json.JSONDecodeError:
            pass

        # If standard parsing fails and json_repair is available, try repair
        if repair_json is not None:
            try:
                repaired = repair_json(text)
                parsed = json.loads(repaired)
                return parsed, True
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

        # If all else fails, return empty dict with failure status
        return {}, False

    def _call_ollama(
        self, prompt: str, schema_name: str = "translate", stage_label: str = "General"
    ) -> Optional[str]:
        """Call Ollama API with extended timeout for large prompts."""
        if not self._check_ollama_connection():
            return None

        if OLLAMA_STREAMING:
            return self._call_ollama_streaming(prompt, schema_name, stage_label)

        # Determine token limits based on schema
        num_predict = 16384
        if schema_name == "linguistic":
            num_predict = 32768  # Extended for detailed linguistic analysis
        elif schema_name in ["detailed", "questions"]:
            num_predict = 16384

        try:
            response = requests.post(
                f"{OLLAMA_API_BASE}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "think": True,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": num_predict,
                        "num_ctx": 16384,
                    },
                },
                timeout=OLLAMA_TIMEOUT,
            )

            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "").strip()
                thinking_text = result.get("thinking", "").strip()

                if not response_text and thinking_text:
                    response_text = thinking_text

                return response_text
            else:
                return None

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            Exception,
        ):
            return None

    def _call_ollama_streaming(
        self, prompt: str, schema_name: str = "translate", stage_label: str = "General"
    ) -> Optional[str]:
        """Call Ollama API using streaming mode for better handling of long responses."""
        if not self._check_ollama_connection():
            return None

        # Determine token limits based on schema
        num_predict = 16384  # Default increased from 8192
        if schema_name == "linguistic":
            num_predict = 32768  # Extended for detailed linguistic analysis
        elif schema_name in ["detailed", "questions"]:
            num_predict = 16384

        try:
            response = requests.post(
                f"{OLLAMA_API_BASE}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": num_predict,
                        "num_ctx": 8192,
                    },
                },
                timeout=OLLAMA_TIMEOUT,
                stream=True,
            )

            if response.status_code == 200:
                full_response = ""
                thinking_text = ""

                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        full_response += chunk.get("response", "")
                        if chunk.get("thinking"):
                            thinking_text += chunk.get("thinking", "")

                if not full_response and thinking_text:
                    full_response = thinking_text

                return full_response.strip()
            else:
                return None

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            Exception,
        ):
            return None

    def _generate_initial_translation_with_dict(
        self, text: str, schema_name: str = "translate"
    ) -> Tuple[str, str]:
        """Generate initial translation using dictionary hints."""
        dictionary_entries = self._lookup_dictionary_entries(text)
        glossary_text = self._format_dictionary_prompt(dictionary_entries)

        user_payload = json.dumps(
            {"input_text": text, "dictionary_matches": dictionary_entries},
            ensure_ascii=False,
        )

        translation_only_system = """You are an expert translator. You will receive a JSON payload of the form {"input_text": "<text_here>"}. Translate the entire text fluently and respond ONLY with valid JSON:
{
  "translated_text": "<translated_text>"
}
Do not include any other keys, explanations, or commentary. Ensure the JSON is valid and double-quoted."""

        prompt = (
            f"System: {translation_only_system}\n\nUser: {user_payload}\n\nAssistant:"
        )

        response_text = self._call_ollama(prompt, schema_name)
        clean_response = self._clean_thinking(response_text) if response_text else ""

        translated = text
        try:
            parsed = json.loads(clean_response)
            translated = parsed.get("translated_text", text).strip()
        except json.JSONDecodeError:
            translated = clean_response.strip() or text

        return translated, json.dumps(dictionary_entries, ensure_ascii=False)

    def _generate_initial_translation(self, text: str) -> Tuple[str, str]:
        """Stage 1: Generate initial translation using Ollama with dictionary hints."""
        dictionary_entries = self._lookup_dictionary_entries(text)
        glossary_text = self._format_dictionary_prompt(dictionary_entries)

        attempts = [
            {
                "label": "Translation-only Stage",
                "system_prompt": TRANSLATION_ONLY_SYSTEM_PROMPT,
                "user_payload": json.dumps(
                    {"input_text": text, "dictionary_matches": dictionary_entries},
                    ensure_ascii=False,
                ),
            },
            {
                "label": "Translation retry (plain text)",
                "system_prompt": TRANSLATION_ONLY_FALLBACK_PROMPT,
                "user_payload": f"{text}\n\nDictionary hints (local BDIC):\n{glossary_text}",
            },
        ]

        for idx, attempt in enumerate(attempts):
            prompt = f"System: {attempt['system_prompt']}\n\nUser: {attempt['user_payload']}\n\nAssistant:"
            raw = self._call_ollama(prompt, stage_label=attempt["label"])
            clean = self._clean_thinking(raw) if raw else ""
            candidate = self._extract_translated_text(clean)

            if candidate:
                return candidate, clean

        return text, text

    def _extract_translated_text(self, response_text: str) -> str:
        """Extract translated_text field from JSON response."""
        if not isinstance(response_text, str):
            return ""
        try:
            parsed = json.loads(response_text)
            candidate = parsed.get("translated_text", "")
            if isinstance(candidate, str):
                return candidate.strip()
        except Exception:
            pass
        return response_text.strip()

    def translate_with_qwen(
        self, text: str, schema_name: str = "translate"
    ) -> Dict[str, Any]:
        """
        Translate using Qwen via Ollama with two-stage refinement pipeline.
        Stage 1: Generate initial translation with dictionary hints
        Stage 2: Refine translation and add explanations (using selected schema)
        """
        if not self._check_ollama_connection():
            return {
                "success": False,
                "model": "qwen",
                "error": "Qwen/Ollama not available",
            }

        try:
            schema = PromptingSchemaRegistry.get_or_default(schema_name)

            if schema.name == "detailed":
                system_prompt = schema.get_system_prompt()
                user_payload = schema.get_user_payload(text, None)

                final_prompt = (
                    f"System: {system_prompt}\n\nUser: {user_payload}\n\nAssistant:"
                )
                final_response = self._call_ollama(
                    final_prompt, stage_label="Detailed Analysis"
                )

                if not final_response:
                    return {
                        "success": False,
                        "model": "qwen",
                        "error": "No response from Ollama",
                    }

                final_response = self._clean_thinking(final_response)
                parsed_result = schema.parse_response(final_response)
                parsed_result["success"] = True
                parsed_result["model"] = "qwen"
                return parsed_result

            initial_translation, _ = self._generate_initial_translation(text)
            initial_translation = initial_translation.strip()

            system_prompt = schema.get_system_prompt()
            user_payload = schema.get_user_payload(text, initial_translation)

            final_prompt = (
                f"System: {system_prompt}\n\nUser: {user_payload}\n\nAssistant:"
            )
            final_response = self._call_ollama(
                final_prompt, stage_label="Refinement Stage"
            )

            if not final_response:
                return {
                    "success": False,
                    "model": "qwen",
                    "error": "No response from Ollama",
                }

            final_response = self._clean_thinking(final_response)
            parsed_result = schema.parse_response(final_response)
            parsed_result["initial_translation"] = initial_translation
            parsed_result["success"] = True
            parsed_result["model"] = "qwen"

            return parsed_result

        except Exception as e:
            return {"success": False, "model": "qwen", "error": str(e)}

    def translate(
        self, text: str, schema_name: str = "translate", models: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Translate text using Qwen via Ollama with dictionary enrichment.

        Args:
            text: Input text to translate
            schema_name: Prompting schema to use
            models: Deprecated - ignored (only Qwen is supported)

        Returns:
            Dictionary with translation from Qwen
        """
        result = {
            "input_text": text,
            "schema_used": schema_name,
            "model": "qwen",
        }

        result["translation"] = self.translate_with_qwen(text, schema_name)
        return result

    def generate_questions(self, text: str, question_count: int = 5) -> Dict[str, Any]:
        """Generate HSK-style multiple-choice reading comprehension questions."""
        if not self._check_ollama_connection():
            return {
                "success": False,
                "error": "Qwen/Ollama not available",
            }

        try:
            question_count = max(1, min(question_count, 20))

            schema = PromptingSchemaRegistry.get_or_default("questions")

            system_prompt = schema.get_system_prompt()
            user_payload = schema.get_user_payload(text, question_count)

            prompt = f"System: {system_prompt}\n\nUser: {user_payload}\n\nAssistant:"
            response_text = self._call_ollama(
                prompt, schema_name="questions", stage_label="Question Generation"
            )

            if not response_text:
                return {
                    "success": False,
                    "error": "No response from Ollama",
                }

            response_text = self._clean_thinking(response_text)
            parsed_result = schema.parse_response(response_text)
            parsed_result["success"] = True
            parsed_result["question_count"] = question_count

            return parsed_result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def analyze_linguistic(self, full_text: str, selected_text: str) -> Dict[str, Any]:
        """
        Perform linguistic analysis of selected text within a larger text.

        Args:
            full_text: Complete Chinese text for context
            selected_text: The specific portion to analyze

        Returns:
            Dictionary with linguistic analysis results
        """
        if not self._check_ollama_connection():
            return {
                "success": False,
                "error": "Qwen/Ollama not available",
            }

        try:
            schema = PromptingSchemaRegistry.get_or_default("linguistic")

            system_prompt = schema.get_system_prompt()
            user_payload = schema.get_user_payload(full_text, selected_text)

            prompt = f"System: {system_prompt}\n\nUser: {user_payload}\n\nAssistant:"
            response_text = self._call_ollama(
                prompt, schema_name="linguistic", stage_label="Linguistic Analysis"
            )

            if not response_text:
                return {
                    "success": False,
                    "error": "No response from Ollama",
                }

            response_text = self._clean_thinking(response_text)
            parsed_result = schema.parse_response(response_text)

            # Check if parse_response failed (indicated by presence of 'error' key)
            if "error" in parsed_result:
                return {
                    "success": False,
                    "error": parsed_result.get("error", "Unknown parse error"),
                    "raw_response": parsed_result.get("raw_response"),
                }

            parsed_result["success"] = True

            return parsed_result

        except Exception as e:
            return {"success": False, "error": str(e)}
