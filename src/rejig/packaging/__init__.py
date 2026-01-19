"""Package manager configuration management.

This package provides tools for parsing, manipulating, and converting Python
package manager configurations across different formats.

Supported Formats
-----------------
- requirements.txt (pip)
- pyproject.toml (PEP 621 standard)
- Poetry pyproject.toml
- UV pyproject.toml

Classes
-------
Dependency
    Unified representation of a Python dependency.

PackageMetadata
    Package metadata (name, version, authors, etc.).

PackageConfig
    Complete package configuration.

RequirementsParser
    Parse requirements.txt files.

PEP621Parser
    Parse PEP 621 pyproject.toml files.

PoetryParser
    Parse Poetry pyproject.toml files.

UVParser
    Parse UV pyproject.toml files.

FormatDetector
    Detect package configuration format.

PackageConfigConverter
    Convert between different formats.

Examples
--------
>>> from rejig import Rejig
>>>
>>> # Using Rejig integration
>>> rj = Rejig(".")
>>> config = rj.get_package_config()
>>> if config:
...     print(f"Format: {config.format}")
...     for dep in config.dependencies:
...         print(f"  {dep.name}: {dep.version_spec}")
>>>
>>> # Add a dependency
>>> rj.add_dependency("requests", ">=2.28.0")
>>>
>>> # Add a dev dependency
>>> rj.add_dependency("pytest", ">=7.0", dev=True)
>>>
>>> # Export as requirements.txt
>>> rj.export_requirements()
>>>
>>> # Convert Poetry to PEP 621
>>> rj.convert_package_config("pep621")

>>> # Using parsers directly
>>> from rejig.packaging import RequirementsParser, PEP621Parser
>>> from pathlib import Path
>>>
>>> # Parse requirements.txt
>>> parser = RequirementsParser()
>>> config = parser.parse(Path("requirements.txt"))
>>>
>>> # Parse pyproject.toml
>>> parser = PEP621Parser()
>>> config = parser.parse(Path("pyproject.toml"))
"""

from rejig.packaging.converter import (
    PackageConfigConverter,
    convert_poetry_to_pep621,
    export_requirements,
)
from rejig.packaging.detector import (
    FormatDetector,
    detect_format,
    get_package_config,
)
from rejig.packaging.models import (
    Dependency,
    PackageConfig,
    PackageFormat,
    PackageMetadata,
)
from rejig.packaging.pep621 import PEP621Parser, parse_pep621
from rejig.packaging.poetry import PoetryParser, parse_poetry
from rejig.packaging.requirements import RequirementsParser, parse_requirements
from rejig.packaging.uv import UVParser, parse_uv

__all__ = [
    # Models
    "Dependency",
    "PackageMetadata",
    "PackageConfig",
    "PackageFormat",
    # Parsers
    "RequirementsParser",
    "PEP621Parser",
    "PoetryParser",
    "UVParser",
    # Detection
    "FormatDetector",
    "detect_format",
    "get_package_config",
    # Conversion
    "PackageConfigConverter",
    "convert_poetry_to_pep621",
    "export_requirements",
    # Convenience functions
    "parse_requirements",
    "parse_pep621",
    "parse_poetry",
    "parse_uv",
]
