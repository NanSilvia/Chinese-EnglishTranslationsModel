"""
Extensible prompting schemas for different translation analysis approaches.
New schemas can be added by inheriting from BasePromptingSchema.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
import json

try:
    from json_repair import repair_json
except ImportError:
    repair_json = None


class BasePromptingSchema(ABC):
    """
    Abstract base class for prompting schemas.
    Extend this to add new prompting strategies.
    """

    name: str = "base"
    description: str = "Base schema"

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this schema."""
        pass

    @abstractmethod
    def get_user_payload(
        self, text: str, initial_translation: Optional[str] = None
    ) -> str:
        """Return the user payload/prompt for this schema."""
        pass

    @abstractmethod
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the model response according to this schema."""
        pass

    def _safe_json_parse(self, text: str) -> Tuple[Dict[str, Any], bool]:
        """
        Safely parse JSON with repair fallback.

        Returns:
            Tuple of (parsed_dict, success_bool)
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


class TranslateSchema(BasePromptingSchema):
    """
    Default two-stage translation schema with dictionary integration.
    Stage 1: Initial translation with dictionary hints
    Stage 2: Refinement with grammatical/phrasal explanations
    """

    name = "translate"
    description = "Two-stage schema with dictionary and explanations"

    def get_system_prompt(self) -> str:
        return """You are an expert translator and language analyst. You will receive text in a JSON format that must be translated and explained. Your task is to:

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

    def get_user_payload(
        self, text: str, initial_translation: Optional[str] = None
    ) -> str:
        payload = {
            "input_text": text,
        }
        if initial_translation:
            payload["initial_translation"] = initial_translation
        return json.dumps(payload, ensure_ascii=False)

    def parse_response(self, response: str) -> Dict[str, Any]:
        parsed, success = self._safe_json_parse(response)
        if not success:
            return {
                "translated_text": response,
                "explanations": [],
                "raw_response": response,
                "error": "Failed to parse JSON response",
            }
        return {
            "translated_text": parsed.get("translated_text", ""),
            "explanations": parsed.get("explainations_list", []),
            "raw_response": response,
        }


class SimpleSchema(BasePromptingSchema):
    """
    Simple translation-only schema without explanations.
    Fast and lightweight for basic translation needs.
    """

    name = "simple"
    description = "Simple translation-only schema"

    def get_system_prompt(self) -> str:
        return """You are an expert translator. You will receive a JSON payload of the form {"input_text": "<text_here>"}. Translate the entire text fluently and respond ONLY with valid JSON:
{
  "translated_text": "<translated_text>"
}
Do not include any other keys, explanations, or commentary. Ensure the JSON is valid and double-quoted."""

    def get_user_payload(
        self, text: str, initial_translation: Optional[str] = None
    ) -> str:
        payload = {"input_text": text}
        return json.dumps(payload, ensure_ascii=False)

    def parse_response(self, response: str) -> Dict[str, Any]:
        parsed, success = self._safe_json_parse(response)
        if not success:
            return {
                "translated_text": response,
                "raw_response": response,
                "error": "Failed to parse JSON response",
            }
        return {
            "translated_text": parsed.get("translated_text", ""),
            "raw_response": response,
        }


class DetailedSchema(BasePromptingSchema):
    """Detailed schema with extended analysis including cultural context and stylistic notes."""

    name = "detailed"
    description = "Detailed schema with cultural and stylistic analysis"

    def get_system_prompt(self) -> str:
        return """You are an expert translator with deep knowledge of Chinese language, culture, and linguistics.

You will receive a JSON input with Chinese text. Analyze it thoroughly and respond with ONLY a JSON object - nothing else.

The JSON you must return must have EXACTLY these keys:
- "translated_text": The complete English translation
- "grammatical_analysis": Array of [structure, explanation] pairs
- "challenging_phrases": Array of [phrase, explanation] pairs  
- "cultural_context": String or null
- "stylistic_notes": String or null
- "alternative_interpretations": Array of strings or null

CRITICAL: Do NOT use "explainations_list" - that is wrong for this schema.

Example output format:
{
  "translated_text": "The translation here",
  "grammatical_analysis": [["structure1", "explanation1"]],
  "challenging_phrases": [["phrase1", "explanation1"]],
  "cultural_context": "any cultural notes here",
  "stylistic_notes": "any stylistic observations",
  "alternative_interpretations": ["alt1", "alt2"]
}

Respond with ONLY valid JSON. No other text before or after."""

    def get_user_payload(
        self, text: str, initial_translation: Optional[str] = None
    ) -> str:
        payload = {
            "input_text": text,
        }
        if initial_translation:
            payload["initial_translation"] = initial_translation
        return json.dumps(payload, ensure_ascii=False)

    def parse_response(self, response: str) -> Dict[str, Any]:
        parsed, success = self._safe_json_parse(response)
        if not success:
            return {
                "translated_text": response,
                "raw_response": response,
                "error": "Failed to parse JSON response",
            }
        return {
            "translated_text": parsed.get("translated_text", ""),
            "grammatical_analysis": parsed.get("grammatical_analysis", []),
            "challenging_phrases": parsed.get("challenging_phrases", []),
            "cultural_context": parsed.get("cultural_context"),
            "stylistic_notes": parsed.get("stylistic_notes"),
            "alternative_interpretations": parsed.get("alternative_interpretations"),
            "raw_response": response,
        }






class PromptingSchemaRegistry:
    """Registry for managing available prompting schemas."""

    _schemas: Dict[str, BasePromptingSchema] = {}

    @classmethod
    def register(cls, schema: BasePromptingSchema) -> None:
        """Register a new prompting schema."""
        cls._schemas[schema.name] = schema

    @classmethod
    def get(cls, name: str) -> Optional[BasePromptingSchema]:
        """Get a prompting schema by name."""
        return cls._schemas.get(name)

    @classmethod
    def list_schemas(cls) -> Dict[str, str]:
        """List all available schemas with descriptions."""
        return {name: schema.description for name, schema in cls._schemas.items()}

    @classmethod
    def get_or_default(cls, name: str) -> BasePromptingSchema:
        """Get a schema or return the default one."""
        schema = cls.get(name)
        if schema is None:
            schema = cls.get("translate")
        return schema


# Initialize registry with built-in schemas
PromptingSchemaRegistry.register(TranslateSchema())
PromptingSchemaRegistry.register(SimpleSchema())
PromptingSchemaRegistry.register(DetailedSchema())