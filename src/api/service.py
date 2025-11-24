"""
Translation service module with Qwen/Ollama integration.
Handles model inference and response processing with dictionary enrichment.
"""

import json
from typing import Optional, Dict, Any, Tuple

from .config import DEFAULT_AGENT
from .schemas import PromptingSchemaRegistry
from .ollama_client import OllamaClient
from .dictionary import lookup_dictionary_entries, format_dictionary_prompt


# Translation system prompts
TRANSLATION_ONLY_SYSTEM_PROMPT = """You are an expert translator. You will receive a JSON payload of the form {"input_text": "<text_here>"}. Translate the entire text fluently and respond ONLY with valid JSON:
{
  "translated_text": "<translated_text>"
}
Do not include any other keys, explanations, or commentary. Ensure the JSON is valid and double-quoted."""

TRANSLATION_ONLY_FALLBACK_PROMPT = """You are an expert translator. Translate the user's message into fluent English. Respond with the translated sentence only—no JSON, commentary, or metadata."""


class TranslationService:
    """Handles translation operations using configured agent."""

    def __init__(self):
        self.default_agent = DEFAULT_AGENT
        self.ollama_client = OllamaClient()

    def _check_ollama_connection(self) -> bool:
        """Check if Ollama is available."""
        return self.ollama_client.check_connection()

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

    def _generate_initial_translation(self, text: str) -> Tuple[str, str]:
        """Stage 1: Generate initial translation using Ollama with dictionary hints."""
        dictionary_entries = lookup_dictionary_entries(text)
        glossary_text = format_dictionary_prompt(dictionary_entries)

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
            raw = self.ollama_client.call_ollama(prompt, stage_label=attempt["label"])
            clean = self.ollama_client.clean_thinking(raw) if raw else ""
            candidate = self._extract_translated_text(clean)

            if candidate:
                return candidate, clean

        return text, text

    def summarize_text(
        self,
        text: str,
        language: str = "chi",
        length: str = "medium",
        style: str = "neutral",
    ) -> Dict[str, Any]:
        """
        Summarize text in the specified language.

        Args:
            text: Text to summarize
            language: Language code
            length: Summary length (short, medium, long)
            style: Summary style (neutral, simple, academic)

        Returns:
            Dictionary with summary and key points
        """
        if not self._check_ollama_connection():
            return {
                "success": False,
                "error": "Ollama not available",
                "summary": "",
                "key_points": [],
            }

        # Build length instruction
        length_instructions = {
            "short": "1-2 sentences",
            "medium": "3-5 sentences",
            "long": "a full paragraph (6-10 sentences)",
        }
        length_instruction = length_instructions.get(length, "3-5 sentences")

        # Build style instruction
        style_instructions = {
            "neutral": "Use neutral, objective language.",
            "simple": "Use simple, easy-to-understand language suitable for beginners.",
            "academic": "Use formal, academic language.",
        }
        style_instruction = style_instructions.get(
            style, "Use neutral, objective language."
        )

        # Build the prompt based on language
        if language == "chi":
            prompt = f"""请总结以下中文文本。

重要提示：请仅基于提供的原文内容进行总结，不要添加任何外部知识、假设或推断。总结必须完全来源于给定的文本。

原文：
{text}

要求：
- 总结长度：{length_instruction}
- 写作风格：{style_instruction}
- 提取3-5个关键要点

请先在<think>标签内分析文本的主要内容和结构，然后提供JSON回复：
{{
  "summary": "总结内容",
  "key_points": ["要点1", "要点2", "要点3"]
}}

只返回JSON，不要其他文字。"""
        else:
            prompt = f"""Summarize the following text.

IMPORTANT: Base your summary ONLY on information explicitly stated in the provided text. Do not add any external knowledge, assumptions, or inferences. The summary must be entirely derived from the given text.

Original text:
{text}

Requirements:
- Summary length: {length_instruction}
- Writing style: {style_instruction}
- Extract 3-5 key points

First, analyze the main content and structure of the text within <think> tags, then respond in JSON format:
{{
  "summary": "summary text",
  "key_points": ["point 1", "point 2", "point 3"]
}}

Respond ONLY with valid JSON."""

        try:
            # Use lower temperature and higher context for more accurate, grounded summaries
            response = self.ollama_client.call_ollama(
                prompt,
                schema_name="translate",
                stage_label="Text Summarization",
                temperature=0.3,
                num_ctx=32768,
            )

            if response:
                cleaned = self.ollama_client.clean_thinking(response)
                parsed, success = self.ollama_client.safe_json_parse(cleaned)

                if success:
                    return {
                        "success": True,
                        "summary": parsed.get("summary", ""),
                        "key_points": parsed.get("key_points", []),
                    }

            return {
                "success": False,
                "error": "Failed to parse AI response",
                "summary": "",
                "key_points": [],
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": "",
                "key_points": [],
            }

    def analyze_word(
        self,
        word: str,
        context: Optional[str] = None,
        language: str = "chi",
        include_synonyms: bool = True,
        include_antonyms: bool = True,
        include_alternatives: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze a word and provide synonyms, antonyms, and alternative wordings.

        Args:
            word: The word to analyze
            context: Optional context sentence
            language: Language code
            include_synonyms: Whether to include synonyms
            include_antonyms: Whether to include antonyms
            include_alternatives: Whether to include alternative wordings

        Returns:
            Dictionary with word analysis
        """
        if not self._check_ollama_connection():
            return {
                "success": False,
                "error": "Ollama not available",
                "synonyms": [],
                "antonyms": [],
                "alternative_wordings": [],
                "usage_examples": [],
            }  # Build the analysis prompt based on language
        if language == "chi":
            prompt = f"""Analyze the Chinese word/phrase: {word}

{f'Context sentence: {context}' if context else 'No context provided.'}

Provide a comprehensive analysis as JSON with these fields:
- synonyms: list of synonyms (similar meanings)
- antonyms: list of antonyms (opposite meanings)
- alternative_wordings: list of alternative ways to express the same idea
- usage_examples: list of 3 example sentences using this word
- explanation: brief explanation of the word's meaning and usage

Consider the context if provided. Respond ONLY with valid JSON."""
        else:
            prompt = f"""Analyze the word: {word}

{f'Context sentence: {context}' if context else 'No context provided.'}

Provide a comprehensive analysis as JSON with these fields:
- synonyms: list of synonyms (similar meanings)
- antonyms: list of antonyms (opposite meanings) 
- alternative_wordings: list of alternative ways to express the same idea
- usage_examples: list of 3 example sentences using this word
- explanation: brief explanation of the word's meaning and usage

Consider the context if provided. Respond ONLY with valid JSON."""

        try:
            response = self.ollama_client.call_ollama(
                prompt, schema_name="translate", stage_label="Word Analysis"
            )

            if response:
                cleaned = self.ollama_client.clean_thinking(response)
                parsed, success = self.ollama_client.safe_json_parse(cleaned)

                if success:
                    result = {
                        "success": True,
                        "synonyms": (
                            parsed.get("synonyms", []) if include_synonyms else []
                        ),
                        "antonyms": (
                            parsed.get("antonyms", []) if include_antonyms else []
                        ),
                        "alternative_wordings": (
                            parsed.get("alternative_wordings", [])
                            if include_alternatives
                            else []
                        ),
                        "usage_examples": parsed.get("usage_examples", []),
                        "explanation": parsed.get("explanation"),
                    }
                    return result

            return {
                "success": False,
                "error": "Failed to parse AI response",
                "synonyms": [],
                "antonyms": [],
                "alternative_wordings": [],
                "usage_examples": [],
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "synonyms": [],
                "antonyms": [],
                "alternative_wordings": [],
                "usage_examples": [],
            }

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
                final_response = self.ollama_client.call_ollama(
                    final_prompt,
                    schema_name=schema_name,
                    stage_label="Detailed Analysis",
                )

                if not final_response:
                    return {
                        "success": False,
                        "model": "qwen",
                        "error": "No response from Ollama",
                    }

                final_response = self.ollama_client.clean_thinking(final_response)
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
            final_response = self.ollama_client.call_ollama(
                final_prompt, schema_name=schema_name, stage_label="Refinement Stage"
            )

            if not final_response:
                return {
                    "success": False,
                    "model": "qwen",
                    "error": "No response from Ollama",
                }

            final_response = self.ollama_client.clean_thinking(final_response)
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
            response_text = self.ollama_client.call_ollama(
                prompt, schema_name="questions", stage_label="Question Generation"
            )

            if not response_text:
                return {
                    "success": False,
                    "error": "No response from Ollama",
                }

            response_text = self.ollama_client.clean_thinking(response_text)
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
            response_text = self.ollama_client.call_ollama(
                prompt, schema_name="linguistic", stage_label="Linguistic Analysis"
            )

            if not response_text:
                return {
                    "success": False,
                    "error": "No response from Ollama",
                }

            response_text = self.ollama_client.clean_thinking(response_text)
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
