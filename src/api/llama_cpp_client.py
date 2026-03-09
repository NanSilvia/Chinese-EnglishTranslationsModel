"""
llama.cpp API client for interacting with served language models.
Uses the OpenAI-compatible API that llama.cpp server exposes.
"""

import json
import re
import requests
from typing import Optional, Tuple, Dict, Any

from .config import (
    LLAMA_CPP_API_BASE,
    LLAMA_CPP_MODEL,
    LLAMA_CPP_TIMEOUT,
    LLAMA_CPP_STREAMING,
)

try:
    from json_repair import repair_json
except ImportError:
    repair_json = None


class LlamaCppClient:
    """Client for interacting with llama.cpp's OpenAI-compatible API."""

    def __init__(self):
        self.connected = None

    def check_connection(self) -> bool:
        """Check if llama.cpp server is available."""
        if self.connected is not None:
            return self.connected

        try:
            response = requests.get(f"{LLAMA_CPP_API_BASE}/health", timeout=5)
            if response.status_code == 200:
                self.connected = True
                return True
        except Exception:
            pass

        # Fallback: try the models endpoint (OpenAI-compatible)
        try:
            response = requests.get(f"{LLAMA_CPP_API_BASE}/v1/models", timeout=5)
            if response.status_code == 200:
                self.connected = True
                return True
        except Exception as e:
            print(f"llama.cpp connection failed: {e}")

        self.connected = False
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

    def call_generate(
        self,
        prompt: str,
        schema_name: str = "translate",
        stage_label: str = "General",
        temperature: float = 0.7,
        num_ctx: int = 16384,
        model: Optional[str] = None,
    ) -> Optional[str]:
        """Call llama.cpp API using the OpenAI-compatible completions endpoint.

        Args:
            prompt: The prompt to send to the model
            schema_name: Schema type for determining token limits
            stage_label: Label for the processing stage
            temperature: Controls randomness (0.0-1.0, lower = more focused)
            num_ctx: Context window size in tokens
            model: Override the default model
        """
        if not self.check_connection():
            return None

        # Use provided model or fall back to default
        model_to_use = model if model else LLAMA_CPP_MODEL

        if LLAMA_CPP_STREAMING:
            return self._call_streaming(
                prompt, schema_name, stage_label, temperature, num_ctx, model_to_use
            )

        # Determine max_tokens based on schema
        max_tokens = 16384
        if schema_name == "linguistic":
            max_tokens = 32768  # Extended for detailed linguistic analysis
        elif schema_name in ["detailed", "questions"]:
            max_tokens = 16384

        try:
            response = requests.post(
                f"{LLAMA_CPP_API_BASE}/v1/completions",
                json={
                    "model": model_to_use,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "stream": False,
                },
                timeout=LLAMA_CPP_TIMEOUT,
            )

            if response.status_code == 200:
                result = response.json()
                choices = result.get("choices", [])
                if choices:
                    response_text = choices[0].get("text", "").strip()
                    return response_text
                return None
            else:
                print(f"llama.cpp API error: {response.status_code} - {response.text}")
                return None

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            Exception,
        ) as e:
            print(f"llama.cpp request failed: {e}")
            return None

    def _call_streaming(
        self,
        prompt: str,
        schema_name: str = "translate",
        stage_label: str = "General",
        temperature: float = 0.7,
        num_ctx: int = 16384,
        model: Optional[str] = None,
    ) -> Optional[str]:
        """Call llama.cpp API using streaming mode for better handling of long responses.

        Args:
            prompt: The prompt to send to the model
            schema_name: Schema type for determining token limits
            stage_label: Label for the processing stage
            temperature: Controls randomness (0.0-1.0, lower = more focused)
            num_ctx: Context window size in tokens
            model: Override the default model
        """
        if not self.check_connection():
            return None

        # Use provided model or fall back to default
        model_to_use = model if model else LLAMA_CPP_MODEL

        # Determine max_tokens based on schema
        max_tokens = 16384
        if schema_name == "linguistic":
            max_tokens = 32768
        elif schema_name in ["detailed", "questions"]:
            max_tokens = 16384

        try:
            response = requests.post(
                f"{LLAMA_CPP_API_BASE}/v1/completions",
                json={
                    "model": model_to_use,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "stream": True,
                },
                timeout=LLAMA_CPP_TIMEOUT,
                stream=True,
            )

            if response.status_code == 200:
                full_response = ""

                for line in response.iter_lines():
                    if line:
                        line_str = (
                            line.decode("utf-8") if isinstance(line, bytes) else line
                        )
                        # SSE format: "data: {...}" or "data: [DONE]"
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                choices = chunk.get("choices", [])
                                if choices:
                                    full_response += choices[0].get("text", "")
                            except json.JSONDecodeError:
                                continue

                return full_response.strip() if full_response else None
            else:
                print(
                    f"llama.cpp streaming error: {response.status_code} - {response.text}"
                )
                return None

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            Exception,
        ) as e:
            print(f"llama.cpp streaming request failed: {e}")
            return None

    def call_chat(
        self,
        messages: list,
        schema_name: str = "translate",
        stage_label: str = "General",
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> Optional[str]:
        """Call llama.cpp API using the OpenAI-compatible chat completions endpoint.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            schema_name: Schema type for determining token limits
            stage_label: Label for the processing stage
            temperature: Controls randomness (0.0-1.0, lower = more focused)
            model: Override the default model
        """
        if not self.check_connection():
            return None

        model_to_use = model if model else LLAMA_CPP_MODEL

        max_tokens = 16384
        if schema_name == "linguistic":
            max_tokens = 32768
        elif schema_name in ["detailed", "questions"]:
            max_tokens = 16384

        try:
            response = requests.post(
                f"{LLAMA_CPP_API_BASE}/v1/chat/completions",
                json={
                    "model": model_to_use,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "stream": False,
                },
                timeout=LLAMA_CPP_TIMEOUT,
            )

            if response.status_code == 200:
                result = response.json()
                choices = result.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return message.get("content", "").strip()
                return None
            else:
                print(
                    f"llama.cpp chat API error: {response.status_code} - {response.text}"
                )
                return None

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            Exception,
        ) as e:
            print(f"llama.cpp chat request failed: {e}")
            return None
