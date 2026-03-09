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

# Model Configuration (llama.cpp OpenAI-compatible API)
LLAMA_CPP_API_BASE = os.getenv("LLAMA_CPP_API_BASE", "http://localhost:8080")
LLAMA_CPP_MODEL = os.getenv("LLAMA_CPP_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
LLAMA_CPP_TIMEOUT = int(os.getenv("LLAMA_CPP_TIMEOUT", 600))
LLAMA_CPP_STREAMING = os.getenv("LLAMA_CPP_STREAMING", "true").lower() == "true"

# Agent Configuration
DEFAULT_AGENT = "local"

# Dictionary Configuration
DICTIONARY_BDIC_PATH = os.getenv("DICTIONARY_BDIC_PATH", "./knowledge/en-US-10-1.bdic")

# Dataset Configuration
SAMPLE_SIZE = int(os.getenv("SAMPLE_SIZE", 5))

# Database Configuration (PostgreSQL)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://zhapp:zhapp@localhost:5432/zhapp",
)

# JWT Configuration
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", "CHANGE-ME-in-production-use-a-real-secret"
)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7))

# Rate Limiting
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
RATE_LIMIT_HEAVY = os.getenv("RATE_LIMIT_HEAVY", "20/minute")
