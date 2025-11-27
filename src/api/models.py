"""
Data models for request/response validation using Pydantic.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Status of an async job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TranslationRequest(BaseModel):
    """Base request for translation operations."""

    text: str = Field(..., description="Text to translate (Chinese)")
    schema_name: str = Field(
        default="translate",
        description="Prompting schema to use (e.g., 'translate', 'simple', 'detailed')",
    )


class DictionaryEntry(BaseModel):
    """Dictionary lookup entry."""

    source_term: str
    romanized: str
    suggestions: List[str]


class TranslationResponse(BaseModel):
    """Response from translation endpoint."""

    input_text: str
    translations: Dict[str, Any] = Field(
        ...,
        description="Model-specific translations {'qwen': '...', 'claude': '...', 'google': '...'}",
    )
    dictionary_entries: Optional[List[DictionaryEntry]] = None


class ComparisonAnalysisRequest(BaseModel):
    """Request for semantic comparison analysis."""

    texts: List[str] = Field(..., description="List of texts to analyze")
    schema_name: str = Field(default="translate", description="Prompting schema to use")
    compute_similarities: bool = Field(
        default=True, description="Whether to compute similarity metrics"
    )


class SimilarityMetrics(BaseModel):
    """Semantic similarity metrics."""

    qwen_vs_claude: float
    qwen_vs_google: float
    claude_vs_google: float
    qwen_vs_reference: Optional[float] = None
    claude_vs_reference: Optional[float] = None
    google_vs_reference: Optional[float] = None


class ComparisonAnalysisResponse(BaseModel):
    """Response from comparison analysis endpoint."""

    total_processed: int
    results: List[Dict[str, Any]]
    summary_statistics: Optional[Dict[str, float]] = None


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str
    message: str
    ollama_connected: Optional[bool] = None
    models_available: Optional[List[str]] = None


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None


class AsyncTranslationJob(BaseModel):
    """Async translation job request."""

    text: str = Field(..., description="Text to translate (Chinese)")
    schema_name: str = Field(
        default="translate",
        description="Prompting schema to use (e.g., 'default', 'simple', 'detailed')",
    )


class AsyncQuestionsJob(BaseModel):
    """Async questions generation job request."""

    text: str = Field(..., description="Chinese text to generate questions from")
    question_count: int = Field(
        default=5, description="Number of questions to generate (1-20)"
    )


class QuestionResponse(BaseModel):
    """Response from question generation endpoint."""

    input_text: str
    question_count: int
    questions: Optional[List[Dict[str, Any]]] = None


class AsyncJobResponse(BaseModel):
    """Response for async job submission."""

    job_id: str = Field(..., description="Unique job ID for polling")
    status: JobStatus = Field(..., description="Current job status")
    message: str = Field(..., description="Status message")


class AsyncJobStatusResponse(BaseModel):
    """Response for job status polling."""

    job_id: str
    status: JobStatus
    progress: Optional[str] = None
    result: Optional[Any] = None  # Can be TranslationResponse or QuestionResponse
    error: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class LinguisticAnalysisRequest(BaseModel):
    """Request for linguistic analysis of selected text."""

    full_text: str = Field(
        ..., description="Complete Simplified Chinese text for context"
    )
    selected_text: str = Field(
        ..., description="The specific portion to analyze linguistically"
    )


class AnalyzedTextData(BaseModel):
    """Data about the analyzed text."""

    chinese: str = Field(..., description="The Chinese text that was analyzed")
    pinyin: str = Field(..., description="Pinyin with tone marks")


class GrammarPattern(BaseModel):
    """A grammar pattern found in the analyzed text."""

    pattern: str = Field(..., description="Grammar pattern name/structure")
    structure: str = Field(..., description="Abstract formula")
    example_in_text: Dict[str, str] = Field(
        ..., description="Example with chinese and pinyin"
    )
    explanation: str = Field(..., description="Explanation of the pattern")


class LinguisticAnalysisResponse(BaseModel):
    """Response from linguistic analysis endpoint."""

    analyzed_text: AnalyzedTextData
    expansion_note: Optional[str] = Field(
        None, description="Note if expansion was needed"
    )
    english_translation: str = Field(..., description="English translation")
    sentence_structure_explanation: str = Field(
        ..., description="Detailed breakdown of syntactic structure"
    )
    grammatical_rule_explanation: str = Field(
        ..., description="Explanation of grammar rules and patterns"
    )
    grammar_patterns: List[GrammarPattern] = Field(
        ..., description="List of grammar patterns found"
    )


class AsyncLinguisticJob(BaseModel):
    """Async linguistic analysis job request."""

    full_text: str = Field(..., description="Complete Chinese text for context")
    selected_text: str = Field(..., description="Text portion to analyze")

