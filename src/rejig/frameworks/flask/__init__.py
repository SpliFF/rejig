"""Flask-specific refactoring tools.

Provides FlaskProject class for managing Flask application routes,
blueprints, error handlers, and related operations.
"""
from __future__ import annotations

from .project import FlaskProject

__all__ = ["FlaskProject"]
