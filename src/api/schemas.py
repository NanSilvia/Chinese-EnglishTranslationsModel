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

class QuestionSchema(BasePromptingSchema):
    """Question generation schema based on input text and desired number of output questions."""

    name = "questions"
    description = "questions based on provided text"

    def get_system_prompt(self):
        return """You are an expert HSK exam question writer.

Your task:
Given a JSON object as input, read the Chinese text in "input_text" and generate HSK-style multiple-choice reading-comprehension questions.

All generated content for the questions MUST be in **simplified Chinese only**  
(no Pinyin, no English).

--------------------
INPUT FORMAT
--------------------
{
  "input_text": "<input_text>",
  "question_count": <number_of_questions>
}

- "input_text": a short Chinese text (article, dialogue, story, etc.)
- "question_count": the number of questions to create.

--------------------
QUESTION REQUIREMENTS
--------------------
1. Create exactly "question_count" questions based on the input_text.
2. The difficulty and style should match official HSK reading questions
   (ask about main idea, details, inference, word meaning in context, etc.).
3. Each question must be a single-sentence prompt in Chinese.
4. Each question MUST have 4 answer options in Chinese.
5. Only ONE option is correct.
6. All questions and options must rely ONLY on the information in input_text
   (no outside knowledge, no contradictions).
7. The options should be:
   - Grammatically correct
   - Similar length and style
   - Plausible but clearly wrong for the incorrect ones
8. Do NOT number or label options with A/B/C/D inside the text.
   Just provide plain strings.

--------------------
OUTPUT FORMAT (JSON ONLY)
--------------------
Return ONLY a JSON object in the following structure, with no extra text:

{
  "questions_list": [
    {
      "question_prompt": "<question_in_Chinese_1>",
      "possible_answers": [
        "<option_1_in_Chinese>",
        "<option_2_in_Chinese>",
        "<option_3_in_Chinese>",
        "<option_4_in_Chinese>"
      ],
      "correct_answer_index": <0_or_1_or_2_or_3>
    }
    // ... more questions
  ]
}

- "correct_answer_index" is the zero-based index of the correct option
  in "possible_answers" (0 = first option, 1 = second, etc.).
- Do not include any additional fields.
- Do not output explanations or reasoning, only the JSON object.
"""

    def get_user_payload(self, text: str, question_count: int) -> str:
        payload = {
            "input_text": text,
            "question_count": question_count,
        }
        return json.dumps(payload, ensure_ascii=False)

    def parse_response(self, response: str) -> Dict[str, Any]:
        parsed, success = self._safe_json_parse(response)
        if not success:
            return {
                "response_text": response,
                "error": "Failed to parse JSON response",
            }
        return {
            "questions_list": parsed.get("questions_list", []),
        }

class LinguisticSchema(BasePromptingSchema):
    """
    Linguistic analysis schema for selected text of a bigger text
    """

    name = "linguistic"
    description = "Linguistic analysis of a selection inside of a larger text"

    def get_system_prompt(self):
        return """You are a Chinese language grammar and structure analysis assistant. You will receive input in the following JSON format:

{"full_text": "<full_text>", "selected_text": "<selected_text>"}

Where:
- full_text: The complete Simplified Chinese text/sentence (used for context only)
- selected_text: The specific portion the user wants analyzed

## Your Task:

1. **Identify the selected_text** within the full_text context

2. **Determine scope of analysis:**
   - If selected_text is a complete grammatical unit → analyze ONLY the selected_text
   - If selected_text is an incomplete grammatical structure (e.g., half a clause, partial phrase) → expand ONLY to the minimum necessary to capture the complete grammatical unit, and explicitly note this expansion

3. **Provide your response in the following JSON format:**

```json
{
  "analyzed_text": {
    "chinese": "<the Chinese text you analyzed>",
    "pinyin": "<pinyin with tone marks for the analyzed text>"
  },
  "expansion_note": null | "<briefly explain why expansion was needed>",
  "english_translation": "<accurate English translation of the analyzed text>",
  "sentence_structure_explanation": "<detailed breakdown of the syntactic structure of the analyzed text: identify subject, predicate, object, complements, modifiers, and how they relate to each other; include pinyin when referencing specific words/phrases; use linguistic terminology where appropriate>",
  "grammatical_rule_explanation": "<explain the specific Chinese grammar rules, patterns, or constructions present ONLY in the analyzed text; include pinyin when referencing specific words; cover relevant word order, particles, aspect markers, or other Mandarin-specific features>",
  "grammar_patterns": [
    {
      "pattern": "<grammar pattern name/structure found in analyzed text>",
      "structure": "<abstract formula e.g., S + 把 + O + V + complement>",
      "example_in_text": {
        "chinese": "<how this pattern appears in the analyzed text>",
        "pinyin": "<pinyin for the example>"
      },
      "explanation": "<brief explanation of this pattern's function and usage>"
    }
  ]
}
```

## Guidelines:
- Analyze ONLY within the scope of selected_text (or minimally expanded text)
- Extract grammar patterns ONLY from the analyzed text, NOT from full_text
- Always include pinyin (with tone marks: ā á ǎ à) alongside Chinese references in explanations
- Keep explanations clear and educational
- Use standard grammatical terminology (SVO, topic-comment, 把-construction, 是...的 structure, resultative complement, etc.)
- Note structural differences between Chinese and English when relevant
- If the analyzed text contains idioms (成语) or set phrases, explain both their structure as a unit and their literal composition
- The full_text is for contextual understanding only — do not analyze or extract patterns from portions outside the analyzed text
"""

    def get_user_payload(self, full_text: str, selected_text: str) -> str:
        """Generate JSON payload for linguistic analysis."""
        payload = {
            "full_text": full_text,
            "selected_text": selected_text,
        }
        return json.dumps(payload, ensure_ascii=False)

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the linguistic analysis response."""
        parsed, success = self._safe_json_parse(response)
        if not success:
            return {
                "error": "Failed to parse JSON response",
                "raw_response": response,
            }
        return {
            "analyzed_text": parsed.get("analyzed_text", {}),
            "expansion_note": parsed.get("expansion_note"),
            "english_translation": parsed.get("english_translation", ""),
            "sentence_structure_explanation": parsed.get(
                "sentence_structure_explanation", ""
            ),
            "grammatical_rule_explanation": parsed.get(
                "grammatical_rule_explanation", ""
            ),
            "grammar_patterns": parsed.get("grammar_patterns", []),
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
PromptingSchemaRegistry.register(QuestionSchema())
PromptingSchemaRegistry.register(LinguisticSchema())