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


# OpenLibrary Book Models
class BookSummary(BaseModel):
    """Summary of a book from OpenLibrary."""

    title: str
    authors: List[str] = Field(default_factory=list)
    first_publish_year: Optional[int] = None
    isbn: Optional[str] = None
    subjects: List[str] = Field(default_factory=list)
    publishers: List[str] = Field(default_factory=list)
    language: List[str] = Field(default_factory=list)
    number_of_pages: Optional[int] = None
    openlibrary_key: Optional[str] = None
    cover_id: Optional[int] = None
    has_fulltext: bool = False


class BookSearchRequest(BaseModel):
    """Request for book search."""

    query: str = Field(..., description="Search query (title, author, ISBN, etc.)")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results")
    author: Optional[str] = Field(None, description="Filter by author")
    subject: Optional[str] = Field(None, description="Filter by subject")
    place: Optional[str] = Field(None, description="Filter by place")
    person: Optional[str] = Field(None, description="Filter by person")
    language: Optional[str] = Field(
        None,
        description="Filter by language (e.g., 'chi' for Chinese, 'eng' for English, 'jpn' for Japanese)",
    )


class BookSearchResponse(BaseModel):
    """Response from book search."""

    query: str
    num_found: int
    results: List[BookSummary]


class BookRecommendationRequest(BaseModel):
    """Request for book recommendations based on text."""

    text: str = Field(..., description="Text to analyze for recommendations")
    limit: int = Field(default=5, ge=1, le=20, description="Number of recommendations")
    prefer_diverse_authors: bool = Field(
        default=True, description="Prefer books from different authors"
    )


class BookRecommendationResponse(BaseModel):
    """Response with book recommendations."""

    text_length: int
    keywords: List[str]
    num_found: int
    recommendations: List[BookSummary]


class TextResearchRequest(BaseModel):
    """Request for researching related books for translated text."""

    original_text: str = Field(..., description="Original Chinese text")
    translated_text: Optional[str] = Field(
        None, description="English translation (optional)"
    )
    limit: int = Field(
        default=5, ge=1, le=20, description="Number of book recommendations"
    )
    language: Optional[str] = Field(
        None, description="Filter by language code (e.g., 'chi', 'eng', 'jpn')"
    )


class TextResearchResponse(BaseModel):
    """Response with translation and book recommendations."""

    original_text: str
    translated_text: str
    keywords: List[str]
    book_recommendations: List[BookSummary]
    num_books_found: int


class TextDifficultyMetrics(BaseModel):
    """Difficulty metrics for a text."""

    character_count: int
    unique_characters: int
    word_count: int
    avg_word_length: float
    complexity_score: float = Field(
        ..., description="Overall complexity score (0-100, higher = more difficult)"
    )
    difficulty_level: str = Field(
        ..., description="Difficulty level: beginner, intermediate, advanced, native"
    )
    hsk_level: Optional[int] = Field(
        None, description="HSK level (1-6) for Chinese text, determined by AI"
    )
    vocabulary_complexity: Optional[str] = Field(
        None, description="AI analysis of vocabulary complexity"
    )
    grammar_complexity: Optional[str] = Field(
        None, description="AI analysis of grammar complexity"
    )
    estimated_study_hours: Optional[int] = Field(
        None, description="Estimated total study hours needed to read this level"
    )


class SimilarTextResult(BaseModel):
    """A text with similar difficulty level."""

    title: str
    authors: List[str]
    text_preview: Optional[str] = None
    difficulty_metrics: TextDifficultyMetrics
    openlibrary_key: str
    language: List[str]
    subjects: List[str]


class TextDifficultyRequest(BaseModel):
    """Request for finding texts of similar difficulty."""

    original_text: str = Field(..., description="Original text to analyze")
    language: str = Field(
        default="chi", description="Language code (e.g., 'chi', 'eng', 'jpn')"
    )
    limit: int = Field(
        default=5, ge=1, le=20, description="Number of similar texts to find"
    )


class TextDifficultyResponse(BaseModel):
    """Response with difficulty analysis and similar texts."""

    original_text: str
    difficulty_metrics: TextDifficultyMetrics
    similar_texts: List[SimilarTextResult]
    num_found: int


class WordAnalysisRequest(BaseModel):
    """Request for word analysis with context."""

    word: str = Field(..., description="Word to analyze")
    context: Optional[str] = Field(
        None, description="Context sentence containing the word"
    )
    language: str = Field(
        default="chi", description="Language code (e.g., 'chi', 'eng', 'jpn')"
    )
    include_synonyms: bool = Field(default=True, description="Include synonyms")
    include_antonyms: bool = Field(default=True, description="Include antonyms")
    include_alternatives: bool = Field(
        default=True, description="Include alternative wordings"
    )


class WordAnalysisResponse(BaseModel):
    """Response with word analysis including synonyms, antonyms, and alternatives."""

    word: str
    context: Optional[str]
    language: str
    synonyms: List[str] = Field(default_factory=list)
    antonyms: List[str] = Field(default_factory=list)
    alternative_wordings: List[str] = Field(default_factory=list)
    usage_examples: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None


class SummarizationRequest(BaseModel):
    """Request for text summarization."""

    text: str = Field(..., description="Text to summarize")
    language: str = Field(
        default="chi", description="Language code (e.g., 'chi', 'eng', 'jpn')"
    )
    length: str = Field(
        default="medium",
        description="Summary length: 'short' (1-2 sentences), 'medium' (3-5 sentences), 'long' (paragraph)",
    )
    style: str = Field(
        default="neutral",
        description="Summary style: 'neutral', 'simple' (easy to understand), 'academic' (formal)",
    )


class SummarizationResponse(BaseModel):
    """Response with text summary."""

    original_text: str
    summary: str
    language: str
    length: str
    style: str
    key_points: List[str] = Field(default_factory=list)
    word_count_original: int
    word_count_summary: int
