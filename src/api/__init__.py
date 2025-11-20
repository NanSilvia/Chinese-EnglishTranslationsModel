"""
Main FastAPI application with REST endpoints.
Single-agent mode: configured default agent is used for all translations.
Async mode: long-running translations are handled asynchronously with polling.
"""

from fastapi import FastAPI
import asyncio

from .config import API_DEBUG, DEFAULT_AGENT
from .routes import router as main_router, get_translation_service
from .routes_async import router as async_router, get_job_manager
from .routes_books import router as books_router

# Initialize FastAPI app
app = FastAPI(
    title="Translation Analysis API with Book Research",
    description=f"REST API for Chinese-English translation analysis using {DEFAULT_AGENT.upper()} model with OpenLibrary book search integration",
    version="2.1.0",
)

# Include routers
app.include_router(main_router)
app.include_router(async_router)
app.include_router(books_router)


@app.on_event("startup")
async def startup_event():
    """Start the async job processor when the app starts."""
    job_manager = get_job_manager()
    await job_manager.start_worker()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup when the app shuts down."""
    job_manager = get_job_manager()
    job_manager.cleanup_old_jobs(max_age_seconds=300)
