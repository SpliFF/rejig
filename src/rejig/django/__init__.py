"""
Django-specific refactoring utilities.

This subpackage provides tools for refactoring Django projects, including:
- Settings management (INSTALLED_APPS, MIDDLEWARE, custom settings)
- URL configuration management
- Dependency management (pyproject.toml)
- App creation and discovery
- Code movement using rope

Example
-------
>>> from rejig.django import DjangoProject
>>>
>>> # Initialize project
>>> project = DjangoProject("/path/to/project")
>>>
>>> # Add an app to INSTALLED_APPS
>>> project.add_installed_app("newapp", after_app="django.contrib.auth")
>>>
>>> # Add a URL include
>>> project.add_url_include("myapp.urls", path_prefix="api/")
>>>
>>> # Always close when done (cleans up rope)
>>> project.close()
"""
from __future__ import annotations

from .project import DjangoProject

__all__ = [
    "DjangoProject",
]
