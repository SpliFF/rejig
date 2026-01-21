"""FastAPI-specific refactoring tools.

Provides FastAPIProject class for managing FastAPI endpoints,
dependencies, middleware, and Pydantic models.
"""
from __future__ import annotations

from .project import FastAPIProject

__all__ = ["FastAPIProject"]
