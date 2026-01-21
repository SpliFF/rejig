"""
Shared pytest fixtures for the Rejig test suite.

This module provides:
- Temporary directory fixtures with sample Python files
- Pre-configured Rejig instances (normal and dry-run modes)
- Sample config files (TOML, YAML, JSON, INI)
- Helper functions for creating test files

Fixture Naming Convention:
- tmp_* : Fixtures that create temporary directories/files
- sample_* : Fixtures that provide sample content strings
- rejig_* : Fixtures that provide configured Rejig instances
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Generator

import pytest

from rejig import Rejig


# =============================================================================
# Sample Python Code Fixtures
# =============================================================================

@pytest.fixture
def sample_class_code() -> str:
    """
    Sample Python code with a simple class.

    Contains:
    - A class with __init__, public method, and private method
    - Class attribute with type annotation
    - Docstrings on class and methods
    - Decorator on one method
    """
    return textwrap.dedent('''
        """Module with a sample class."""
        from typing import Optional


        class MyClass:
            """A sample class for testing.

            This class demonstrates various Python features
            that can be refactored.
            """

            count: int = 0

            def __init__(self, name: str, value: int = 0) -> None:
                """Initialize the class.

                Args:
                    name: The name of the instance.
                    value: Initial value, defaults to 0.
                """
                self.name = name
                self.value = value
                MyClass.count += 1

            def process(self, data: str) -> str:
                """Process the given data.

                Args:
                    data: Input data to process.

                Returns:
                    Processed data string.
                """
                return f"{self.name}: {data}"

            @staticmethod
            def helper() -> str:
                """A static helper method."""
                return "helper"

            def _private_method(self) -> None:
                """A private method."""
                pass
    ''').strip()


@pytest.fixture
def sample_function_code() -> str:
    """
    Sample Python code with module-level functions.

    Contains:
    - Functions with various signatures (typed, untyped, defaults)
    - Decorated functions
    - Async functions
    - Functions without docstrings (for docstring generation tests)
    """
    return textwrap.dedent('''
        """Module with sample functions."""
        import asyncio
        from functools import lru_cache
        from typing import List, Optional


        def simple_function(x: int, y: int) -> int:
            """Add two numbers."""
            return x + y


        def untyped_function(name, count=0):
            """Function without type hints."""
            return name * count


        @lru_cache(maxsize=128)
        def cached_function(n: int) -> int:
            """Fibonacci with caching."""
            if n < 2:
                return n
            return cached_function(n - 1) + cached_function(n - 2)


        async def async_function(url: str) -> str:
            """An async function."""
            await asyncio.sleep(0.1)
            return f"fetched: {url}"


        def function_without_docstring(a, b, c):
            result = a + b + c
            return result


        def complex_function(
            items: List[str],
            separator: str = ",",
            prefix: Optional[str] = None,
        ) -> str:
            """Join items with optional prefix."""
            joined = separator.join(items)
            if prefix:
                return f"{prefix}{joined}"
            return joined
    ''').strip()


@pytest.fixture
def sample_nested_classes_code() -> str:
    """
    Sample Python code with nested and multiple classes.

    Contains:
    - Parent class with inheritance
    - Child class
    - Nested inner class
    - Abstract base class pattern
    """
    return textwrap.dedent('''
        """Module with multiple and nested classes."""
        from abc import ABC, abstractmethod
        from typing import Any


        class BaseClass(ABC):
            """Abstract base class."""

            @abstractmethod
            def do_something(self) -> Any:
                """Abstract method to be implemented."""
                pass


        class ParentClass(BaseClass):
            """Parent class with nested class."""

            class InnerClass:
                """A nested inner class."""

                def __init__(self, value: int) -> None:
                    self.value = value

                def get_value(self) -> int:
                    return self.value

            def __init__(self) -> None:
                self.inner = self.InnerClass(42)

            def do_something(self) -> int:
                """Implementation of abstract method."""
                return self.inner.get_value()


        class ChildClass(ParentClass):
            """Child class that extends ParentClass."""

            def __init__(self, multiplier: int = 2) -> None:
                super().__init__()
                self.multiplier = multiplier

            def do_something(self) -> int:
                """Override parent implementation."""
                return super().do_something() * self.multiplier
    ''').strip()


@pytest.fixture
def sample_imports_code() -> str:
    """
    Sample Python code with various import styles.

    Contains:
    - Standard library imports
    - Third-party imports (simulated)
    - Relative imports
    - Import aliases
    - Unused imports (for detection tests)
    """
    return textwrap.dedent('''
        """Module with various import styles."""
        import os
        import sys
        from pathlib import Path
        from typing import Dict, List, Optional, Union

        # Third-party imports
        from dataclasses import dataclass, field

        # Unused imports for testing detection
        import json  # unused
        from collections import OrderedDict  # unused

        # Aliased imports
        import datetime as dt
        from typing import Any as AnyType


        @dataclass
        class Config:
            """Configuration class."""

            name: str
            path: Path
            options: Dict[str, AnyType] = field(default_factory=dict)


        def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
            """Get environment variable."""
            return os.environ.get(key, default)


        def list_files(directory: Union[str, Path]) -> List[Path]:
            """List files in a directory."""
            p = Path(directory)
            return list(p.iterdir())
    ''').strip()


@pytest.fixture
def sample_todo_comments_code() -> str:
    """
    Sample Python code with TODO/FIXME/XXX/HACK comments.

    Contains various comment formats for testing TODO detection.
    """
    return textwrap.dedent('''
        """Module with TODO comments."""

        # TODO: Implement caching mechanism
        # FIXME: This function has a bug with negative numbers
        # XXX: Temporary workaround, remove after refactoring
        # HACK: Quick fix for demo, needs proper solution

        def calculate(x: int, y: int) -> int:
            """Calculate something.

            TODO: Add input validation
            """
            # TODO(john): Optimize this algorithm
            # FIXME(jane): Handle edge case when x == 0
            result = x + y  # XXX: This is too simple
            return result


        class DataProcessor:
            """Process data.

            FIXME: Memory leak in process_batch method
            """

            def process(self, data):
                # TODO: Add logging
                # HACK: Hardcoded value for now
                return data * 2
    ''').strip()


@pytest.fixture
def sample_type_hints_code() -> str:
    """
    Sample Python code with old-style type hints for modernization tests.

    Contains:
    - Old-style typing imports (List, Dict, Optional, Union)
    - Type comments
    - Functions needing type hint inference
    """
    return textwrap.dedent('''
        """Module with old-style type hints."""
        from typing import Dict, List, Optional, Tuple, Union


        def old_style_hints(
            items: List[str],
            mapping: Dict[str, int],
            maybe: Optional[str],
            either: Union[int, str],
        ) -> Tuple[List[str], Dict[str, int]]:
            """Function with old-style type hints."""
            return items, mapping


        # Type comments style
        x = []  # type: List[int]
        y = {}  # type: Dict[str, str]


        def no_hints(name, count, enabled):
            """Function without type hints for inference testing."""
            if enabled:
                return name * count
            return ""


        def partial_hints(name: str, count, enabled: bool):
            """Function with partial type hints."""
            return name * count if enabled else ""
    ''').strip()


@pytest.fixture
def sample_security_issues_code() -> str:
    """
    Sample Python code with security issues for security scanning tests.

    Contains:
    - Hardcoded secrets/passwords
    - SQL injection vulnerability
    - Command injection vulnerability
    - Insecure random usage
    """
    return textwrap.dedent('''
        """Module with security issues for testing."""
        import os
        import random
        import subprocess

        # Hardcoded secrets - should be detected
        API_KEY = "sk-1234567890abcdef"
        PASSWORD = "super_secret_password123"
        DATABASE_URL = "postgresql://user:password123@localhost/db"


        def unsafe_query(user_input: str) -> str:
            """SQL injection vulnerability."""
            query = f"SELECT * FROM users WHERE name = '{user_input}'"
            return query


        def unsafe_command(filename: str) -> None:
            """Command injection vulnerability."""
            os.system(f"cat {filename}")
            subprocess.call(f"rm {filename}", shell=True)


        def insecure_random() -> int:
            """Using random instead of secrets for security."""
            return random.randint(0, 1000000)


        def safe_function(x: int) -> int:
            """A safe function with no issues."""
            return x * 2
    ''').strip()


@pytest.fixture
def sample_complexity_code() -> str:
    """
    Sample Python code with varying complexity levels.

    Contains:
    - Simple function (low complexity)
    - Medium complexity function
    - High complexity function with nested conditions
    """
    return textwrap.dedent('''
        """Module with varying complexity levels."""


        def simple_function(x: int) -> int:
            """Low complexity - single path."""
            return x * 2


        def medium_complexity(x: int, y: int) -> str:
            """Medium complexity - few branches."""
            if x > 0:
                if y > 0:
                    return "both positive"
                else:
                    return "x positive, y not"
            else:
                return "x not positive"


        def high_complexity(data: list, threshold: int, mode: str) -> int:
            """High complexity - many branches and loops."""
            result = 0

            for item in data:
                if isinstance(item, int):
                    if item > threshold:
                        if mode == "add":
                            result += item
                        elif mode == "subtract":
                            result -= item
                        elif mode == "multiply":
                            result *= item if result != 0 else item
                        else:
                            pass
                    elif item == threshold:
                        result += 1
                    else:
                        if mode == "add":
                            result += item // 2
                        else:
                            result -= item // 2
                elif isinstance(item, list):
                    for subitem in item:
                        if subitem > 0:
                            result += subitem
                        else:
                            result -= subitem

            return result
    ''').strip()


# =============================================================================
# Sample Config File Fixtures
# =============================================================================

@pytest.fixture
def sample_pyproject_toml() -> str:
    """Sample pyproject.toml content for testing."""
    return textwrap.dedent('''
        [build-system]
        requires = ["hatchling"]
        build-backend = "hatchling.build"

        [project]
        name = "sample-project"
        version = "1.0.0"
        description = "A sample project for testing"
        readme = "README.md"
        requires-python = ">=3.10"
        license = "MIT"
        authors = [
            { name = "Test Author", email = "test@example.com" }
        ]
        dependencies = [
            "requests>=2.28.0",
            "pydantic>=2.0.0",
        ]

        [project.optional-dependencies]
        dev = [
            "pytest>=7.0.0",
            "black>=23.0.0",
        ]

        [project.scripts]
        sample-cli = "sample:main"

        [tool.black]
        line-length = 100
        target-version = ["py310", "py311"]

        [tool.ruff]
        line-length = 100
        select = ["E", "F", "W"]

        [tool.pytest.ini_options]
        testpaths = ["tests"]
        python_files = ["test_*.py"]
    ''').strip()


@pytest.fixture
def sample_yaml_config() -> str:
    """Sample YAML configuration content for testing."""
    return textwrap.dedent('''
        # Sample YAML configuration
        app:
          name: sample-app
          version: "1.0.0"
          debug: false

        database:
          host: localhost
          port: 5432
          name: sample_db
          credentials:
            username: admin
            password: secret

        features:
          - name: feature_a
            enabled: true
          - name: feature_b
            enabled: false

        logging:
          level: INFO
          handlers:
            - console
            - file
    ''').strip()


@pytest.fixture
def sample_json_config() -> str:
    """Sample JSON configuration content for testing."""
    return json.dumps({
        "name": "sample-project",
        "version": "1.0.0",
        "settings": {
            "debug": False,
            "timeout": 30,
            "retries": 3
        },
        "endpoints": [
            {"url": "/api/v1/users", "method": "GET"},
            {"url": "/api/v1/items", "method": "POST"}
        ]
    }, indent=2)


@pytest.fixture
def sample_ini_config() -> str:
    """Sample INI configuration content for testing."""
    return textwrap.dedent('''
        [DEFAULT]
        debug = false
        timeout = 30

        [database]
        host = localhost
        port = 5432
        name = sample_db

        [logging]
        level = INFO
        format = %(asctime)s - %(name)s - %(levelname)s - %(message)s

        [features]
        feature_a = true
        feature_b = false
    ''').strip()


# =============================================================================
# Temporary Directory Fixtures
# =============================================================================

@pytest.fixture
def tmp_python_project(
    tmp_path: Path,
    sample_class_code: str,
    sample_function_code: str,
) -> Path:
    """
    Create a temporary Python project structure.

    Structure:
    tmp_path/
    ├── src/
    │   ├── __init__.py
    │   ├── models.py      (sample_class_code)
    │   └── utils.py       (sample_function_code)
    └── tests/
        └── __init__.py

    Returns the project root path (tmp_path).
    """
    # Create directory structure
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    # Create files
    (src_dir / "__init__.py").write_text('"""Source package."""\n')
    (src_dir / "models.py").write_text(sample_class_code)
    (src_dir / "utils.py").write_text(sample_function_code)
    (tests_dir / "__init__.py").write_text('"""Test package."""\n')

    return tmp_path


@pytest.fixture
def tmp_python_file(tmp_path: Path, sample_class_code: str) -> Path:
    """
    Create a single temporary Python file with sample class code.

    Returns the path to the Python file.
    """
    file_path = tmp_path / "sample.py"
    file_path.write_text(sample_class_code)
    return file_path


@pytest.fixture
def tmp_empty_file(tmp_path: Path) -> Path:
    """
    Create an empty temporary Python file.

    Returns the path to the empty file.
    """
    file_path = tmp_path / "empty.py"
    file_path.write_text("")
    return file_path


@pytest.fixture
def tmp_config_files(
    tmp_path: Path,
    sample_pyproject_toml: str,
    sample_yaml_config: str,
    sample_json_config: str,
    sample_ini_config: str,
) -> Path:
    """
    Create temporary config files for testing config targets.

    Structure:
    tmp_path/
    ├── pyproject.toml
    ├── config.yaml
    ├── config.json
    └── config.ini

    Returns the directory containing the config files.
    """
    (tmp_path / "pyproject.toml").write_text(sample_pyproject_toml)
    (tmp_path / "config.yaml").write_text(sample_yaml_config)
    (tmp_path / "config.json").write_text(sample_json_config)
    (tmp_path / "config.ini").write_text(sample_ini_config)

    return tmp_path


@pytest.fixture
def tmp_security_test_file(tmp_path: Path, sample_security_issues_code: str) -> Path:
    """
    Create a temporary file with security issues for testing.

    Returns the path to the file.
    """
    file_path = tmp_path / "insecure.py"
    file_path.write_text(sample_security_issues_code)
    return file_path


@pytest.fixture
def tmp_todo_file(tmp_path: Path, sample_todo_comments_code: str) -> Path:
    """
    Create a temporary file with TODO comments for testing.

    Returns the path to the file.
    """
    file_path = tmp_path / "todos.py"
    file_path.write_text(sample_todo_comments_code)
    return file_path


@pytest.fixture
def tmp_type_hints_file(tmp_path: Path, sample_type_hints_code: str) -> Path:
    """
    Create a temporary file with old-style type hints for testing.

    Returns the path to the file.
    """
    file_path = tmp_path / "old_types.py"
    file_path.write_text(sample_type_hints_code)
    return file_path


@pytest.fixture
def tmp_complexity_file(tmp_path: Path, sample_complexity_code: str) -> Path:
    """
    Create a temporary file with varying complexity for testing.

    Returns the path to the file.
    """
    file_path = tmp_path / "complexity.py"
    file_path.write_text(sample_complexity_code)
    return file_path


# =============================================================================
# Rejig Instance Fixtures
# =============================================================================

@pytest.fixture
def rejig(tmp_python_project: Path) -> Generator[Rejig, None, None]:
    """
    Create a Rejig instance for the temporary Python project.

    Normal mode - will modify files.
    Uses context manager to ensure cleanup.
    """
    with Rejig(tmp_python_project) as rj:
        yield rj


@pytest.fixture
def rejig_dry_run(tmp_python_project: Path) -> Generator[Rejig, None, None]:
    """
    Create a Rejig instance in dry-run mode.

    Dry-run mode - will NOT modify files, only report what would happen.
    """
    with Rejig(tmp_python_project, dry_run=True) as rj:
        yield rj


@pytest.fixture
def rejig_single_file(tmp_python_file: Path) -> Generator[Rejig, None, None]:
    """
    Create a Rejig instance for a single Python file.
    """
    with Rejig(tmp_python_file) as rj:
        yield rj


@pytest.fixture
def rejig_config(tmp_config_files: Path) -> Generator[Rejig, None, None]:
    """
    Create a Rejig instance for config file testing.
    """
    with Rejig(tmp_config_files) as rj:
        yield rj


# =============================================================================
# Helper Functions
# =============================================================================

def create_python_file(directory: Path, name: str, content: str) -> Path:
    """
    Helper to create a Python file with given content.

    Parameters
    ----------
    directory : Path
        Directory to create the file in.
    name : str
        Filename (should end with .py).
    content : str
        Python source code content.

    Returns
    -------
    Path
        Path to the created file.
    """
    file_path = directory / name
    file_path.write_text(textwrap.dedent(content).strip())
    return file_path


def assert_file_contains(file_path: Path, expected: str) -> None:
    """
    Assert that a file contains the expected string.

    Parameters
    ----------
    file_path : Path
        Path to the file to check.
    expected : str
        String that should be present in the file.

    Raises
    ------
    AssertionError
        If the expected string is not found.
    """
    content = file_path.read_text()
    assert expected in content, f"Expected '{expected}' not found in {file_path}"


def assert_file_not_contains(file_path: Path, not_expected: str) -> None:
    """
    Assert that a file does NOT contain the given string.

    Parameters
    ----------
    file_path : Path
        Path to the file to check.
    not_expected : str
        String that should NOT be present in the file.

    Raises
    ------
    AssertionError
        If the string is found.
    """
    content = file_path.read_text()
    assert not_expected not in content, f"Unexpected '{not_expected}' found in {file_path}"


def normalize_code(code: str) -> str:
    """
    Normalize Python code for comparison by removing extra whitespace.

    Useful for comparing generated code where exact formatting may vary.

    Parameters
    ----------
    code : str
        Python source code.

    Returns
    -------
    str
        Normalized code with consistent whitespace.
    """
    lines = [line.rstrip() for line in code.strip().split('\n')]
    return '\n'.join(lines)
