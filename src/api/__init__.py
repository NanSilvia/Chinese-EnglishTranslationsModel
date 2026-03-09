"""
Main FastAPI application with REST endpoints.
Single-agent mode: configured default agent is used for all translations.
Async mode: long-running translations are handled asynchronously with polling.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import API_DEBUG, DEFAULT_AGENT, RATE_LIMIT_DEFAULT
from .routes import router as main_router, get_translation_service
from .routes_async import router as async_router, get_job_manager
from .routes_books import router as books_router
from .routes_auth import router as auth_router
from .routes_cards import router as cards_router


def _get_rate_limit_key(request: Request) -> str:
    """Use authenticated user ID when available, otherwise fall back to IP."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            from .auth import decode_access_token

            payload = decode_access_token(auth.split(" ", 1)[1])
            return f"user:{payload['sub']}"
        except Exception:
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=_get_rate_limit_key, default_limits=[RATE_LIMIT_DEFAULT])

# Initialize FastAPI app
app = FastAPI(
    title="Translation Analysis API with Book Research",
    description=f"REST API for Chinese-English translation analysis using {DEFAULT_AGENT.upper()} model with OpenLibrary book search integration",
    version="3.0.0",
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS - allow the Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(cards_router)
app.include_router(main_router)
app.include_router(async_router)
app.include_router(books_router)


@app.on_event("startup")
async def startup_event():
    """Start the async job processor and initialise the database."""
    # Ensure DB tables exist (safe no-op if already created via Alembic)
    from .database import init_db

    await init_db()

    job_manager = get_job_manager()
    await job_manager.start_worker()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup when the app shuts down."""
    job_manager = get_job_manager()
    job_manager.cleanup_old_jobs(max_age_seconds=300)
