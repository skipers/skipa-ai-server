"""Compatibility entrypoint for the AI portfolio insights API.

Run with:
    uvicorn api:app --app-dir ai-insights --host 127.0.0.1 --port 8000
"""

from app.main import app

