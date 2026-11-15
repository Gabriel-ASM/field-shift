"""HTTP API (FastAPI). Run with: uvicorn --factory field_shift.api:create_app"""

from .factory import create_app

__all__ = ["create_app"]
