#!/usr/bin/env python3
"""
OpenLibrary MCP Server
Provides book search, information retrieval, and recommendation capabilities
via the Model Context Protocol.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
import httpx
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# OpenLibrary API endpoints
OPENLIBRARY_SEARCH_API = "https://openlibrary.org/search.json"
OPENLIBRARY_WORKS_API = "https://openlibrary.org/works"
OPENLIBRARY_AUTHORS_API = "https://openlibrary.org/authors"
OPENLIBRARY_COVER_API = "https://covers.openlibrary.org/b"

# Create MCP server instance
app = Server("openlibrary-mcp")


async def search_books(
    query: str,
    fields: Optional[List[str]] = None,
    limit: int = 10,
    offset: int = 0,
    **filters,
) -> Dict[str, Any]:
    """
    Search books using OpenLibrary Search API.

    Args:
        query: Search query string
        fields: Specific fields to return
        limit: Maximum number of results
        offset: Starting offset for pagination
        **filters: Additional search filters (author, subject, place, person, etc.)
    """
    params = {
        "q": query,
        "limit": limit,
        "offset": offset,
    }

    # Add optional filters
    if fields:
        params["fields"] = ",".join(fields)

    for key, value in filters.items():
        if value:
            params[key] = value

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(OPENLIBRARY_SEARCH_API, params=params)
        response.raise_for_status()
        return response.json()


async def get_work_details(work_id: str) -> Dict[str, Any]:
    """Get detailed information about a work."""
    work_id = work_id.replace("/works/", "")
    url = f"{OPENLIBRARY_WORKS_API}/{work_id}.json"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def get_author_details(author_id: str) -> Dict[str, Any]:
    """Get detailed information about an author."""
    author_id = author_id.replace("/authors/", "")
    url = f"{OPENLIBRARY_AUTHORS_API}/{author_id}.json"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def search_by_subject(subject: str, limit: int = 10) -> Dict[str, Any]:
    """Search books by subject/topic."""
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
    return await search_books(query=f"subject:{subject}", limit=limit, fields=fields)


async def search_by_author(author: str, limit: int = 10) -> Dict[str, Any]:
    """Search books by author name."""
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
    return await search_books(query=f"author:{author}", limit=limit, fields=fields)


def analyze_text_difficulty(text: str) -> Dict[str, Any]:
    """Analyze text difficulty based on various metrics. Properly handles CJK languages."""
    import unicodedata

    # Remove punctuation and whitespace for clean analysis
    characters = [
        c for c in text if c.strip() and not unicodedata.category(c).startswith("P")
    ]
    character_count = len(characters)
    unique_characters = len(set(characters))

    # Detect if text is primarily CJK (Chinese/Japanese/Korean)
    cjk_count = sum(
        1
        for c in characters
        if "\u4e00" <= c <= "\u9fff"
        or "\u3040" <= c <= "\u309f"
        or "\u30a0" <= c <= "\u30ff"
        or "\uac00" <= c <= "\ud7af"
    )
    is_cjk = cjk_count > character_count * 0.5

    if is_cjk:
        # For CJK: use character count as proxy for words
        word_count = character_count
        avg_word_length = 1.0

        unique_ratio = unique_characters / character_count if character_count > 0 else 0

        # Complexity score for CJK (0-100)
        complexity_score = (
            (unique_ratio * 40)
            + (min(character_count / 50, 1.0) * 30)
            + (min(unique_characters / 30, 1.0) * 30)
        )

        # CJK difficulty thresholds
        if character_count < 10:
            difficulty_level = "beginner"
        elif character_count < 30:
            difficulty_level = "intermediate"
        elif character_count < 60:
            difficulty_level = "advanced"
        else:
            difficulty_level = "native"

    else:
        # For non-CJK: use space-separated words
        words = text.split()
        word_count = len(words)
        avg_word_length = (
            sum(len(w) for w in words) / word_count if word_count > 0 else 0
        )

        unique_ratio = unique_characters / character_count if character_count > 0 else 0

        # Complexity score for alphabetic languages
        complexity_score = (
            (unique_ratio * 25)
            + (min(avg_word_length / 10, 1.0) * 25)
            + (min(word_count / 50, 1.0) * 25)
            + (min(character_count / 200, 1.0) * 25)
        )

        # Alphabetic language thresholds
        if complexity_score < 30:
            difficulty_level = "beginner"
        elif complexity_score < 50:
            difficulty_level = "intermediate"
        elif complexity_score < 70:
            difficulty_level = "advanced"
        else:
            difficulty_level = "native"

    return {
        "character_count": character_count,
        "unique_characters": unique_characters,
        "word_count": word_count,
        "avg_word_length": round(avg_word_length, 2),
        "complexity_score": round(complexity_score, 2),
        "difficulty_level": difficulty_level,
    }


async def find_texts_by_difficulty(
    text: str, language: str = "chi", limit: int = 5
) -> Dict[str, Any]:
    """Find texts with similar difficulty level."""
    difficulty_metrics = analyze_text_difficulty(text)
    difficulty_level = difficulty_metrics["difficulty_level"]

    search_queries = {
        "beginner": ["children", "elementary"],
        "intermediate": ["young adult", "intermediate"],
        "advanced": ["literature", "novel"],
        "native": ["classic", "contemporary"],
    }

    queries = search_queries.get(difficulty_level, ["literature"])
    results = []

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

    for query in queries[:2]:
        search_params = {"q": f"{query} language:{language}", "limit": limit}
        if fields:
            search_params["fields"] = ",".join(fields)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(OPENLIBRARY_SEARCH_API, params=search_params)
            response.raise_for_status()
            search_results = response.json()
            results.extend(search_results.get("docs", []))
            if len(results) >= limit:
                break

    return {
        "difficulty_metrics": difficulty_metrics,
        "results": results[:limit],
        "num_found": len(results),
    }


def format_book_result(doc: Dict[str, Any]) -> str:
    """Format a book search result for display."""
    title = doc.get("title", "Unknown Title")
    authors = ", ".join(doc.get("author_name", ["Unknown Author"]))
    year = doc.get("first_publish_year", "N/A")
    isbn = doc.get("isbn", ["N/A"])[0] if doc.get("isbn") else "N/A"

    subjects = doc.get("subject", [])
    subjects_str = ", ".join(subjects[:5]) if subjects else "N/A"

    key = doc.get("key", "")

    return f"""
Title: {title}
Author(s): {authors}
First Published: {year}
ISBN: {isbn}
Subjects: {subjects_str}
OpenLibrary Key: {key}
""".strip()


@app.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available OpenLibrary resources."""
    return [
        Resource(
            uri="openlibrary://search",
            name="Book Search",
            description="Search for books in OpenLibrary",
            mimeType="application/json",
        ),
        Resource(
            uri="openlibrary://subjects",
            name="Browse Subjects",
            description="Browse books by subject categories",
            mimeType="application/json",
        ),
    ]


@app.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read resource content from OpenLibrary."""
    if uri == "openlibrary://search":
        return json.dumps(
            {
                "description": "Search books using OpenLibrary API",
                "usage": "Use the search_books tool to query",
            }
        )
    elif uri == "openlibrary://subjects":
        return json.dumps(
            {
                "popular_subjects": [
                    "Fiction",
                    "History",
                    "Biography",
                    "Science",
                    "Philosophy",
                    "Psychology",
                    "Art",
                    "Poetry",
                    "Business",
                    "Self-help",
                ]
            }
        )

    raise ValueError(f"Unknown resource: {uri}")


@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available OpenLibrary tools."""
    return [
        Tool(
            name="search_books",
            description="Search for books using OpenLibrary. Supports free-text search and filters.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (title, author, ISBN, etc.)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10,
                    },
                    "author": {
                        "type": "string",
                        "description": "Filter by author name",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Filter by subject/topic",
                    },
                    "place": {
                        "type": "string",
                        "description": "Filter by place",
                    },
                    "person": {
                        "type": "string",
                        "description": "Filter by person",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_book_details",
            description="Get detailed information about a specific book work",
            inputSchema={
                "type": "object",
                "properties": {
                    "work_id": {
                        "type": "string",
                        "description": "OpenLibrary work ID (e.g., /works/OL45883W or OL45883W)",
                    },
                },
                "required": ["work_id"],
            },
        ),
        Tool(
            name="get_author_info",
            description="Get detailed information about an author",
            inputSchema={
                "type": "object",
                "properties": {
                    "author_id": {
                        "type": "string",
                        "description": "OpenLibrary author ID (e.g., /authors/OL23919A or OL23919A)",
                    },
                },
                "required": ["author_id"],
            },
        ),
        Tool(
            name="search_by_subject",
            description="Find books on a specific subject or topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Subject or topic to search for",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["subject"],
            },
        ),
        Tool(
            name="search_by_author",
            description="Find books by a specific author",
            inputSchema={
                "type": "object",
                "properties": {
                    "author": {
                        "type": "string",
                        "description": "Author name to search for",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["author"],
            },
        ),
        Tool(
            name="recommend_books_for_text",
            description="Analyze text and recommend relevant books based on topics, themes, and content",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to analyze for book recommendations",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of recommendations (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="find_texts_by_difficulty",
            description="Find texts with similar difficulty level to the provided text. Useful for language learners to find appropriately challenging reading material.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Sample text to analyze for difficulty level",
                    },
                    "language": {
                        "type": "string",
                        "description": "Language code (e.g., 'chi', 'eng', 'jpn')",
                        "default": "chi",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["text"],
            },
        ),
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool execution requests."""

    try:
        if name == "search_books":
            query = arguments.get("query")
            limit = arguments.get("limit", 10)
            filters = {
                k: v for k, v in arguments.items() if k not in ["query", "limit"] and v
            }

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
            result = await search_books(query, limit=limit, fields=fields, **filters)

            formatted_results = []
            for doc in result.get("docs", [])[:limit]:
                formatted_results.append(format_book_result(doc))

            response = {
                "num_found": result.get("numFound", 0),
                "results": formatted_results,
                "raw_data": result.get("docs", [])[:limit],
            }

            return [
                TextContent(
                    type="text", text=json.dumps(response, indent=2, ensure_ascii=False)
                )
            ]

        elif name == "get_book_details":
            work_id = arguments.get("work_id")
            details = await get_work_details(work_id)

            return [
                TextContent(
                    type="text", text=json.dumps(details, indent=2, ensure_ascii=False)
                )
            ]

        elif name == "get_author_info":
            author_id = arguments.get("author_id")
            info = await get_author_details(author_id)

            return [
                TextContent(
                    type="text", text=json.dumps(info, indent=2, ensure_ascii=False)
                )
            ]

        elif name == "search_by_subject":
            subject = arguments.get("subject")
            limit = arguments.get("limit", 10)

            result = await search_by_subject(subject, limit=limit)

            formatted_results = []
            for doc in result.get("docs", [])[:limit]:
                formatted_results.append(format_book_result(doc))

            response = {
                "subject": subject,
                "num_found": result.get("numFound", 0),
                "results": formatted_results,
            }

            return [
                TextContent(
                    type="text", text=json.dumps(response, indent=2, ensure_ascii=False)
                )
            ]

        elif name == "search_by_author":
            author = arguments.get("author")
            limit = arguments.get("limit", 10)

            result = await search_by_author(author, limit=limit)

            formatted_results = []
            for doc in result.get("docs", [])[:limit]:
                formatted_results.append(format_book_result(doc))

            response = {
                "author": author,
                "num_found": result.get("numFound", 0),
                "results": formatted_results,
            }

            return [
                TextContent(
                    type="text", text=json.dumps(response, indent=2, ensure_ascii=False)
                )
            ]

        elif name == "recommend_books_for_text":
            text = arguments.get("text")
            limit = arguments.get("limit", 5)

            # Extract potential keywords and topics from text
            # Simple keyword extraction (could be enhanced with NLP)
            words = text.lower().split()
            # Filter common words and get unique meaningful terms
            keywords = list(set([w for w in words if len(w) > 4 and w.isalpha()]))[:5]

            # Search using combined keywords
            search_query = " ".join(keywords[:3])
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
            result = await search_books(search_query, limit=limit * 2, fields=fields)

            # Get diverse results
            recommendations = []
            seen_authors = set()

            for doc in result.get("docs", []):
                authors = doc.get("author_name", [])
                author_key = tuple(authors) if authors else ("unknown",)

                # Prioritize diverse authors
                if len(recommendations) < limit:
                    recommendations.append(doc)
                    seen_authors.add(author_key)
                elif author_key not in seen_authors:
                    recommendations.append(doc)
                    seen_authors.add(author_key)

                if len(recommendations) >= limit:
                    break

            formatted_results = []
            for doc in recommendations[:limit]:
                formatted_results.append(format_book_result(doc))

            response = {
                "analyzed_text_length": len(text),
                "extracted_keywords": keywords[:5],
                "recommendations": formatted_results,
                "num_total_found": result.get("numFound", 0),
            }

            return [
                TextContent(
                    type="text", text=json.dumps(response, indent=2, ensure_ascii=False)
                )
            ]

        elif name == "find_texts_by_difficulty":
            text = arguments.get("text")
            language = arguments.get("language", "chi")
            limit = arguments.get("limit", 5)

            # Analyze difficulty and find similar texts
            result = await find_texts_by_difficulty(text, language, limit)

            # Format results
            formatted_results = []
            for doc in result.get("results", []):
                formatted_results.append(format_book_result(doc))

            response = {
                "input_text": text,
                "difficulty_analysis": result["difficulty_metrics"],
                "similar_difficulty_texts": formatted_results,
                "num_found": result["num_found"],
                "language_filter": language,
            }

            return [
                TextContent(
                    type="text", text=json.dumps(response, indent=2, ensure_ascii=False)
                )
            ]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="openlibrary-mcp",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
