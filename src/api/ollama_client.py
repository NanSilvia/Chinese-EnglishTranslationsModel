"""
Ollama API client for interacting with Qwen models.
"""

import json
import re
import requests
from typing import Optional, Tuple, Dict, Any

from .config import (
    OLLAMA_API_BASE,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    OLLAMA_STREAMING,
)

try:
    from json_repair import repair_json
except ImportError:
    repair_json = None


class OllamaClient:
    """Client for interacting with Ollama API."""

    def __init__(self):
        self.ollama_connected = None

    def check_connection(self) -> bool:
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

    def clean_thinking(self, text: str) -> str:
        """Remove thinking tags and markdown code blocks from response."""
        if not isinstance(text, str):
            return text
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
        text = re.sub(r"<think>.*$", "", text, flags=re.S)
        # Remove markdown code block markers (```json or ```)
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()

    def safe_json_parse(self, text: str) -> Tuple[Dict[str, Any], bool]:
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

    def call_ollama(
        self,
        prompt: str,
        schema_name: str = "translate",
        stage_label: str = "General",
        temperature: float = 0.7,
        num_ctx: int = 16384,
    ) -> Optional[str]:
        """Call Ollama API with extended timeout for large prompts.

        Args:
            prompt: The prompt to send to the model
            schema_name: Schema type for determining token limits
            stage_label: Label for the processing stage
            temperature: Controls randomness (0.0-1.0, lower = more focused)
            num_ctx: Context window size in tokens
        """
        if not self.check_connection():
            return None

        if OLLAMA_STREAMING:
            return self._call_ollama_streaming(
                prompt, schema_name, stage_label, temperature, num_ctx
            )

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
                        "temperature": temperature,
                        "top_p": 0.9,
                        "num_predict": num_predict,
                        "num_ctx": num_ctx,
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
        self,
        prompt: str,
        schema_name: str = "translate",
        stage_label: str = "General",
        temperature: float = 0.7,
        num_ctx: int = 16384,
    ) -> Optional[str]:
        """Call Ollama API using streaming mode for better handling of long responses.

        Args:
            prompt: The prompt to send to the model
            schema_name: Schema type for determining token limits
            stage_label: Label for the processing stage
            temperature: Controls randomness (0.0-1.0, lower = more focused)
            num_ctx: Context window size in tokens
        """
        if not self.check_connection():
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
                        "temperature": temperature,
                        "top_p": 0.9,
                        "num_predict": num_predict,
                        "num_ctx": num_ctx,
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
