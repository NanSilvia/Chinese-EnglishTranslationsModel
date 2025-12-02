"""
Main API routes for translation and general endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List
import uuid

from .models import (
    TranslationRequest,
    TranslationResponse,
    HealthCheckResponse,
    WordAnalysisRequest,
    WordAnalysisResponse,
    SummarizationRequest,
    SummarizationResponse,
)
from .service import TranslationService
from .schemas import PromptingSchemaRegistry
from .config import DEFAULT_AGENT

router = APIRouter()


def get_translation_service():
    """Get or create translation service instance."""
    if not hasattr(get_translation_service, "_instance"):
        get_translation_service._instance = TranslationService()
    return get_translation_service._instance


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Check API health and active agent configuration."""
    translation_service = get_translation_service()
    ollama_available = (
        translation_service._check_ollama_connection()
        if DEFAULT_AGENT == "qwen"
        else None
    )

    return HealthCheckResponse(
        status="healthy",
        message=f"API is running with {DEFAULT_AGENT.upper()} agent",
        ollama_connected=ollama_available,
        models_available=[DEFAULT_AGENT],
    )


@router.get("/schemas")
async def list_schemas():
    """List all available prompting schemas."""
    return {"available_schemas": PromptingSchemaRegistry.list_schemas()}


@router.post("/translate", response_model=TranslationResponse)
async def translate(request: TranslationRequest):
    """
    Translate text using the configured default agent.

    The agent (claude, qwen, or google) is set via DEFAULT_AGENT environment variable.

    Example:
    ```json
    {
        "text": "这是一个测试句子",
        "schema_name": "translate"
    }
    ```
    """
    request_id = str(uuid.uuid4())
    translation_service = get_translation_service()

    try:
        # Validate schema exists
        schema = PromptingSchemaRegistry.get_or_default(request.schema_name)

        # Perform translation with configured agent
        translation_result = translation_service.translate(
            text=request.text, schema_name=request.schema_name
        )

        # Check if translation was successful
        translation_data = translation_result.get("translation", {})
        if not translation_data.get("success", False):
            raise HTTPException(
                status_code=503,
                detail=translation_data.get("error", "Translation failed"),
            )

        return TranslationResponse(
            input_text=request.text, translations={DEFAULT_AGENT: translation_data}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


@router.post("/batch/translate")
async def batch_translate(
    texts: List[str], schema_name: str = Query(default="translate")
):
    """
    Translate multiple texts at once using the configured default agent.

    Query parameters:
    - texts: List of texts to translate
    - schema_name: Prompting schema to use (default: "translate")
    """
    translation_service = get_translation_service()

    try:
        results = []

        for text in texts:
            translation_result = translation_service.translate(
                text=text, schema_name=schema_name
            )
            results.append(translation_result)

        return {
            "total_processed": len(results),
            "schema_used": schema_name,
            "agent": DEFAULT_AGENT,
            "results": results,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Batch translation failed: {str(e)}"
        )


@router.get("/")
async def root():
    """API root endpoint with usage information."""
    return {
        "api": "Translation Analysis API with Book Research",
        "version": "2.1.0",
        "active_agent": DEFAULT_AGENT.upper(),
        "features": [
            "Chinese-English Translation",
            "Question Generation",
            "Linguistic Analysis",
            "Book Search & Recommendations via OpenLibrary.org",
        ],
        "endpoints": {
            "health": "GET /health",
            "schemas": "GET /schemas",
            "translate": "POST /translate (synchronous - may timeout for large prompts)",
            "translate/async": "POST /translate/async (asynchronous - returns job_id for polling)",
            "translate/status/{job_id}": "GET /translate/status/{job_id} (poll job status)",
            "batch_translate": "POST /batch/translate",
            "batch_translate/async": "POST /batch/translate/async",
            "questions/async": "POST /questions/async (asynchronous - returns job_id for polling)",
            "questions/status/{job_id}": "GET /questions/status/{job_id} (poll job status)",
            "linguistic/async": "POST /linguistic/async (linguistic analysis - returns job_id for polling)",
            "linguistic/status/{job_id}": "GET /linguistic/status/{job_id} (poll linguistic analysis status)",
            "books": "GET /books (book search & research endpoints)",
            "books/search": "POST /books/search (search for books)",
            "books/recommend": "POST /books/recommend (get book recommendations from text)",
            "books/research": "POST /books/research (translate text and find related books)",
            "books/similar-difficulty": "POST /books/similar-difficulty (find texts at similar difficulty level)",
            "word/analyze": "POST /word/analyze (analyze word for synonyms/antonyms/alternatives)",
            "text/summarize": "POST /text/summarize (summarize text in specified language)",
            "docs": "GET /docs",
            "openapi": "GET /openapi.json",
        },
        "docs_url": "/docs",
        "mcp_server": "MCP server available at mcp_openlibrary/server.py for AI model integration",
        "note": f"All translations use the {DEFAULT_AGENT.upper()} agent configured via DEFAULT_AGENT environment variable. Use async endpoints for long-running tasks that take >60 seconds.",
    }


@router.post("/text/summarize", response_model=SummarizationResponse)
async def summarize_text_endpoint(request: SummarizationRequest):
    """
    Summarize text in the specified language.

    Provides AI-powered text summarization with customizable:
    - Length (short, medium, long)
    - Style (neutral, simple, academic)
    - Language-aware summarization
    - Key points extraction

    Example:
    ```json
    {
        "text": "北京故宫是中国明清两代的皇家宫殿，旧称紫禁城...",
        "language": "chi",
        "length": "medium",
        "style": "simple"
    }
    ```
    """
    translation_service = get_translation_service()

    try:
        result = translation_service.summarize_text(
            text=request.text,
            language=request.language,
            length=request.length,
            style=request.style,
        )

        if not result.get("success", False):
            raise HTTPException(
                status_code=503, detail=result.get("error", "Summarization failed")
            )

        # Count words
        if request.language == "chi":
            word_count_original = len(
                [c for c in request.text if "\u4e00" <= c <= "\u9fff"]
            )
            word_count_summary = len(
                [c for c in result.get("summary", "") if "\u4e00" <= c <= "\u9fff"]
            )
        else:
            word_count_original = len(request.text.split())
            word_count_summary = len(result.get("summary", "").split())

        return SummarizationResponse(
            original_text=request.text,
            summary=result.get("summary", ""),
            language=request.language,
            length=request.length,
            style=request.style,
            key_points=result.get("key_points", []),
            word_count_original=word_count_original,
            word_count_summary=word_count_summary,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")


@router.post("/word/analyze", response_model=WordAnalysisResponse)
async def analyze_word_endpoint(request: WordAnalysisRequest):
    """
    Analyze a word and get synonyms, antonyms, and alternative wordings.

    Provides context-aware word analysis including:
    - Synonyms (similar meanings)
    - Antonyms (opposite meanings)
    - Alternative wordings (different ways to express the same idea)
    - Usage examples
    - Explanation of meaning and usage

    Example:
    ```json
    {
        "word": "高兴",
        "context": "我今天很高兴。",
        "language": "chi",
        "include_synonyms": true,
        "include_antonyms": true,
        "include_alternatives": true
    }
    ```
    """
    translation_service = get_translation_service()

    try:
        result = translation_service.analyze_word(
            word=request.word,
            context=request.context,
            language=request.language,
            include_synonyms=request.include_synonyms,
            include_antonyms=request.include_antonyms,
            include_alternatives=request.include_alternatives,
        )

        if not result.get("success", False):
            raise HTTPException(
                status_code=503, detail=result.get("error", "Word analysis failed")
            )

        return WordAnalysisResponse(
            word=request.word,
            context=request.context,
            language=request.language,
            synonyms=result.get("synonyms", []),
            antonyms=result.get("antonyms", []),
            alternative_wordings=result.get("alternative_wordings", []),
            usage_examples=result.get("usage_examples", []),
            explanation=result.get("explanation"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Word analysis failed: {str(e)}")
