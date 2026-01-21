"""Framework-specific extensions for rejig.

This module provides specialized refactoring tools for popular Python frameworks:
- Flask: Web application routes, blueprints, and error handlers
- FastAPI: Async API endpoints, dependencies, and middleware
- SQLAlchemy: ORM models, relationships, and database operations
"""
from __future__ import annotations

from .fastapi import FastAPIProject
from .flask import FlaskProject
from .sqlalchemy import SQLAlchemyProject

__all__ = [
    "FlaskProject",
    "FastAPIProject",
    "SQLAlchemyProject",
]
