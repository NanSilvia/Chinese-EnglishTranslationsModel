"""
Main entry point for the REST API server.
Run with: python main.py
"""

import uvicorn
from api import app
from api.config import API_HOST, API_PORT, API_DEBUG


if __name__ == "__main__":
    print(f"Starting Translation Analysis API on {API_HOST}:{API_PORT}")
    print(f"Debug mode: {API_DEBUG}")
    print(f"API documentation available at http://{API_HOST}:{API_PORT}/docs")

    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")
