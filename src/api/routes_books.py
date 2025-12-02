"""
Book search and research routes using OpenLibrary API.
"""

from fastapi import APIRouter, HTTPException
from typing import List

from .models import (
    BookSearchRequest,
    BookSearchResponse,
    BookRecommendationRequest,
    BookRecommendationResponse,
    TextResearchRequest,
    TextResearchResponse,
    TextDifficultyRequest,
    TextDifficultyResponse,
    TextDifficultyMetrics,
    SimilarTextResult,
    BookSummary,
)
from .openlibrary_client import OpenLibraryClient
from .service import TranslationService

router = APIRouter(prefix="/books", tags=["books"])


def get_openlibrary_client():
    """Get or create OpenLibrary client instance."""
    if not hasattr(get_openlibrary_client, "_instance"):
        get_openlibrary_client._instance = OpenLibraryClient()
    return get_openlibrary_client._instance


def get_translation_service():
    """Get or create translation service instance."""
    if not hasattr(get_translation_service, "_instance"):
        get_translation_service._instance = TranslationService()
    return get_translation_service._instance


@router.post("/search", response_model=BookSearchResponse)
async def search_books(request: BookSearchRequest):
    """
    Search for books using OpenLibrary API.

    Supports filtering by author, subject, place, person, language, etc.

    Example:
    ```json
    {
        "query": "Chinese history",
        "limit": 10,
        "subject": "history",
        "language": "chi"
    }
    ```

    Language codes: 'chi' (Chinese), 'eng' (English), 'jpn' (Japanese),
    'fre' (French), 'spa' (Spanish), etc.
    """
    client = get_openlibrary_client()

    try:
        # Build filters
        filters = {}
        if request.author:
            filters["author"] = request.author
        if request.subject:
            filters["subject"] = request.subject
        if request.place:
            filters["place"] = request.place
        if request.person:
            filters["person"] = request.person
        if request.language:
            filters["language"] = request.language

        # Search with explicit fields to get complete metadata
        fields = [
            "key",
            "title",
            "author_name",
            "first_publish_year",
            "isbn",
            "subject",
            "publisher",
            "language",
            "number_of_pages_median",
            "cover_i",
            "has_fulltext",
        ]
        results = client.search_books(
            query=request.query, limit=request.limit, fields=fields, **filters
        )

        # Format results
        books = []
        for doc in results.get("docs", []):
            books.append(BookSummary(**client.format_book_summary(doc)))

        return BookSearchResponse(
            query=request.query, num_found=results.get("numFound", 0), results=books
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Book search failed: {str(e)}")


@router.post("/recommend", response_model=BookRecommendationResponse)
async def recommend_books(request: BookRecommendationRequest):
    """
    Analyze text and recommend relevant books.

    Extracts keywords from the text and searches for related books.

    Example:
    ```json
    {
        "text": "I'm interested in ancient Chinese philosophy and Confucianism",
        "limit": 5
    }
    ```
    """
    client = get_openlibrary_client()

    try:
        recommendations = client.recommend_books_for_text(
            text=request.text,
            limit=request.limit,
            prefer_diverse_authors=request.prefer_diverse_authors,
        )

        # Format results
        books = []
        for doc in recommendations.get("recommendations", []):
            books.append(BookSummary(**client.format_book_summary(doc)))

        return BookRecommendationResponse(
            text_length=recommendations["text_length"],
            keywords=recommendations["keywords"],
            num_found=recommendations["num_found"],
            recommendations=books,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Book recommendation failed: {str(e)}"
        )


@router.post("/similar-difficulty", response_model=TextDifficultyResponse)
async def find_similar_difficulty_texts(request: TextDifficultyRequest):
    """
    Find texts of similar difficulty level to the provided text.

    Analyzes the linguistic complexity of the input text and searches for
    books with matching difficulty levels. Useful for language learners
    looking for appropriately challenging reading material.

    Example:
    ```json
    {
        "original_text": "我喜欢看书。今天天气很好。",
        "language": "chi",
        "limit": 5
    }
    ```
    """
    client = get_openlibrary_client()

    try:
        # Analyze difficulty of input text with AI-powered HSK analysis
        difficulty_metrics = client.analyze_text_difficulty(
            request.original_text, language=request.language
        )

        # Find texts with similar difficulty using HSK-based MCP search
        similar_books = client.find_texts_by_difficulty(
            target_metrics=difficulty_metrics,
            language=request.language,
            limit=request.limit * 2,  # Get extra to filter
        )

        # Format results with difficulty analysis
        similar_texts = []
        for doc in similar_books[: request.limit]:
            # Create difficulty metrics for each result
            title = doc.get("title", "")
            # Estimate difficulty from available metadata
            text_sample = title + " " + " ".join(doc.get("subject", [])[:3])
            result_metrics = client.analyze_text_difficulty(
                text_sample, language=request.language
            )

            similar_texts.append(
                SimilarTextResult(
                    title=doc.get("title", "Unknown Title"),
                    authors=doc.get("author_name", ["Unknown Author"]),
                    text_preview=None,
                    difficulty_metrics=TextDifficultyMetrics(**result_metrics),
                    openlibrary_key=doc.get("key", ""),
                    language=doc.get("language", []),
                    subjects=doc.get("subject", [])[:5],
                )
            )

        return TextDifficultyResponse(
            original_text=request.original_text,
            difficulty_metrics=TextDifficultyMetrics(**difficulty_metrics),
            similar_texts=similar_texts,
            num_found=len(similar_books),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Similar difficulty search failed: {str(e)}"
        )


@router.post("/research", response_model=TextResearchResponse)
async def research_text(request: TextResearchRequest):
    """
    Translate Chinese text and find related books for further reading.

    This endpoint combines translation with book recommendations:
    1. Translates the Chinese text to English (if translation not provided)
    2. Analyzes the content to extract topics and keywords
    3. Searches OpenLibrary for relevant books

    Perfect for finding supplementary reading materials based on Chinese texts.

    Example:
    ```json
    {
        "original_text": "北京故宫是中国明清两代的皇家宫殿，建于1406年到1420年。",
        "limit": 5
    }
    ```

    Returns the translation plus a list of recommended books for deeper study.
    """
    client = get_openlibrary_client()
    translation_service = get_translation_service()

    try:
        # Get or generate translation
        if request.translated_text:
            translated = request.translated_text
        else:
            # Translate using the translation service
            result = translation_service.translate(
                text=request.original_text, schema_name="translate"
            )

            translation_data = result.get("translation", {})
            if not translation_data.get("success"):
                raise HTTPException(
                    status_code=503,
                    detail="Translation failed: "
                    + translation_data.get("error", "Unknown error"),
                )

            translated = translation_data.get("translated_text", request.original_text)

        # Get book recommendations based on translated text
        recommendations = client.recommend_books_for_text(
            text=translated,
            limit=request.limit,
            prefer_diverse_authors=True,
            language=request.language,
        )

        # Format results
        books = []
        for doc in recommendations.get("recommendations", []):
            books.append(BookSummary(**client.format_book_summary(doc)))

        return TextResearchResponse(
            original_text=request.original_text,
            translated_text=translated,
            keywords=recommendations["keywords"],
            book_recommendations=books,
            num_books_found=recommendations["num_found"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text research failed: {str(e)}")


@router.get("/subject/{subject}")
async def get_books_by_subject(subject: str, limit: int = 10):
    """
    Get books on a specific subject/topic.

    Example: /books/subject/chinese-history?limit=10
    """
    client = get_openlibrary_client()

    try:
        results = client.search_by_subject(subject, limit=limit)

        books = []
        for doc in results.get("docs", []):
            books.append(client.format_book_summary(doc))

        return {
            "subject": subject,
            "num_found": results.get("numFound", 0),
            "books": books,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Subject search failed: {str(e)}")


@router.get("/author/{author}")
async def get_books_by_author(author: str, limit: int = 10):
    """
    Get books by a specific author.

    Example: /books/author/Lu%20Xun?limit=10
    """
    client = get_openlibrary_client()

    try:
        results = client.search_by_author(author, limit=limit)

        books = []
        for doc in results.get("docs", []):
            books.append(client.format_book_summary(doc))

        return {
            "author": author,
            "num_found": results.get("numFound", 0),
            "books": books,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Author search failed: {str(e)}")


@router.get("/work/{work_id}")
async def get_work_details(work_id: str):
    """
    Get detailed information about a specific work.

    Example: /books/work/OL45883W
    """
    client = get_openlibrary_client()

    try:
        details = client.get_work_details(work_id)

        if "error" in details:
            raise HTTPException(
                status_code=404, detail=f"Work not found: {details['error']}"
            )

        return details

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get work details: {str(e)}"
        )


@router.get("/author-info/{author_id}")
async def get_author_info(author_id: str):
    """
    Get detailed information about an author.

    Example: /books/author-info/OL23919A
    """
    client = get_openlibrary_client()

    try:
        info = client.get_author_details(author_id)

        if "error" in info:
            raise HTTPException(
                status_code=404, detail=f"Author not found: {info['error']}"
            )

        return info

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get author info: {str(e)}"
        )


@router.get("/")
async def books_root():
    """Book API information."""
    return {
        "name": "OpenLibrary Book Search & Research API",
        "version": "1.0.0",
        "description": "Search for books, get recommendations, and research related reading materials",
        "endpoints": {
            "search": "POST /books/search - Search books with filters",
            "recommend": "POST /books/recommend - Get book recommendations from text",
            "research": "POST /books/research - Translate Chinese text and find related books",
            "subject": "GET /books/subject/{subject} - Browse by subject",
            "author": "GET /books/author/{author} - Browse by author",
            "work": "GET /books/work/{work_id} - Get work details",
            "author_info": "GET /books/author-info/{author_id} - Get author information",
        },
        "data_source": "OpenLibrary.org",
        "mcp_server": "Available at mcp_openlibrary/server.py",
    }
