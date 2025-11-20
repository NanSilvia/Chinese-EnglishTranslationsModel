"""
Configuration module for the translation analysis API.
Handles environment variables, API keys, and model configurations.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
API_DEBUG = os.getenv("API_DEBUG", "false").lower() == "true"

# Model Configuration
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:10000")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:latest")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", 600))
OLLAMA_STREAMING = os.getenv("OLLAMA_STREAMING", "true").lower() == "true"

# Agent Configuration
DEFAULT_AGENT = "qwen"

# Dictionary Configuration
DICTIONARY_BDIC_PATH = os.getenv("DICTIONARY_BDIC_PATH", "./knowledge/en-US-10-1.bdic")

# Dataset Configuration
SAMPLE_SIZE = int(os.getenv("SAMPLE_SIZE", 5))
