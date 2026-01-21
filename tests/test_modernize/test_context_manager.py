"""
Tests for rejig.modernize.context_manager module.

This module tests context manager conversion:
- ConvertToContextManagerTransformer
"""
from __future__ import annotations

import textwrap

import libcst as cst
import pytest

from rejig.modernize.context_manager import ConvertToContextManagerTransformer


# =============================================================================
# ConvertToContextManagerTransformer Initialization Tests
# =============================================================================

class TestConvertToContextManagerTransformerInit:
    """Tests for ConvertToContextManagerTransformer initialization."""

    def test_init_basic(self):
        """Should initialize with class name and defaults."""
        transformer = ConvertToContextManagerTransformer("MyClass")
        assert transformer.class_name == "MyClass"
        assert transformer.converted is False
        assert transformer.enter_body is None
        assert transformer.exit_body is None

    def test_init_with_custom_bodies(self):
        """Should accept custom enter/exit bodies."""
        enter = "self.connect()\nreturn self"
        exit = "self.disconnect()"
        transformer = ConvertToContextManagerTransformer(
            "MyClass",
            enter_body=enter,
            exit_body=exit,
        )
        assert transformer.enter_body == enter
        assert transformer.exit_body == exit


# =============================================================================
# Basic Conversion Tests
# =============================================================================

class TestBasicConversion:
    """Tests for basic context manager conversion."""

    def test_convert_simple_class(self):
        """Should add __enter__ and __exit__ to simple class."""
        code = textwrap.dedent('''\
            class MyClass:
                def __init__(self):
                    pass
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer("MyClass")
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert transformer.converted is True
        assert "def __enter__" in result
        assert "def __exit__" in result

    def test_no_convert_wrong_class(self):
        """Should not convert class with different name."""
        code = textwrap.dedent('''\
            class OtherClass:
                def __init__(self):
                    pass
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer("MyClass")
        new_tree = tree.visit(transformer)

        assert transformer.converted is False
        assert "__enter__" not in new_tree.code

    def test_no_convert_existing_context_manager(self):
        """Should not convert class already a context manager."""
        code = textwrap.dedent('''\
            class MyClass:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer("MyClass")
        new_tree = tree.visit(transformer)

        assert transformer.converted is False
        # Should still have exactly one __enter__ and __exit__
        assert new_tree.code.count("def __enter__") == 1
        assert new_tree.code.count("def __exit__") == 1


# =============================================================================
# Open/Close Method Detection Tests
# =============================================================================

class TestOpenCloseDetection:
    """Tests for classes with open/close methods."""

    def test_detect_open_method(self):
        """Should use open() method in __enter__."""
        code = textwrap.dedent('''\
            class FileHandler:
                def open(self):
                    self.file = open(self.path)

                def close(self):
                    self.file.close()
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer("FileHandler")
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert transformer.converted is True
        assert "def __enter__" in result
        assert "self.open()" in result

    def test_detect_close_method(self):
        """Should use close() method in __exit__."""
        code = textwrap.dedent('''\
            class FileHandler:
                def open(self):
                    self.file = open(self.path)

                def close(self):
                    self.file.close()
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer("FileHandler")
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert transformer.converted is True
        assert "def __exit__" in result
        assert "self.close()" in result


# =============================================================================
# Connect/Disconnect Method Detection Tests
# =============================================================================

class TestConnectDisconnectDetection:
    """Tests for classes with connect/disconnect methods."""

    def test_detect_connect_method(self):
        """Should use connect() method in __enter__."""
        code = textwrap.dedent('''\
            class DatabaseConnection:
                def connect(self):
                    self.conn = create_connection()

                def disconnect(self):
                    self.conn.close()
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer("DatabaseConnection")
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert transformer.converted is True
        assert "def __enter__" in result
        assert "self.connect()" in result

    def test_detect_disconnect_method(self):
        """Should use disconnect() method in __exit__."""
        code = textwrap.dedent('''\
            class DatabaseConnection:
                def connect(self):
                    self.conn = create_connection()

                def disconnect(self):
                    self.conn.close()
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer("DatabaseConnection")
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert transformer.converted is True
        assert "def __exit__" in result
        assert "self.disconnect()" in result


# =============================================================================
# Custom Body Tests
# =============================================================================

class TestCustomBodies:
    """Tests for custom enter/exit bodies."""

    def test_custom_enter_body(self):
        """Should use custom enter body."""
        code = textwrap.dedent('''\
            class MyClass:
                def __init__(self):
                    pass
        ''')
        tree = cst.parse_module(code)

        custom_enter = "self.setup()\nself.validate()\nreturn self"
        transformer = ConvertToContextManagerTransformer(
            "MyClass",
            enter_body=custom_enter,
        )
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert transformer.converted is True
        assert "self.setup()" in result
        assert "self.validate()" in result

    def test_custom_exit_body(self):
        """Should use custom exit body."""
        code = textwrap.dedent('''\
            class MyClass:
                def __init__(self):
                    pass
        ''')
        tree = cst.parse_module(code)

        custom_exit = "self.cleanup()\nself.log_exit()\nreturn None"
        transformer = ConvertToContextManagerTransformer(
            "MyClass",
            exit_body=custom_exit,
        )
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert transformer.converted is True
        assert "self.cleanup()" in result
        assert "self.log_exit()" in result


# =============================================================================
# Default Behavior Tests
# =============================================================================

class TestDefaultBehavior:
    """Tests for default enter/exit behavior."""

    def test_default_enter_returns_self(self):
        """Default __enter__ should return self."""
        code = textwrap.dedent('''\
            class MyClass:
                def __init__(self):
                    pass
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer("MyClass")
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert "return self" in result

    def test_default_exit_returns_none(self):
        """Default __exit__ should return None."""
        code = textwrap.dedent('''\
            class MyClass:
                def __init__(self):
                    pass
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer("MyClass")
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert "return None" in result


# =============================================================================
# Method Signature Tests
# =============================================================================

class TestMethodSignatures:
    """Tests for generated method signatures."""

    def test_enter_has_self_parameter(self):
        """__enter__ should have self parameter."""
        code = textwrap.dedent('''\
            class MyClass:
                pass
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer("MyClass")
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert "def __enter__(self)" in result

    def test_exit_has_standard_parameters(self):
        """__exit__ should have standard exception parameters."""
        code = textwrap.dedent('''\
            class MyClass:
                pass
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer("MyClass")
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert "exc_type" in result
        assert "exc_val" in result
        assert "exc_tb" in result


# =============================================================================
# Partial Context Manager Tests
# =============================================================================

class TestPartialContextManager:
    """Tests for classes with only one context manager method."""

    def test_add_missing_exit(self):
        """Should add __exit__ if only __enter__ exists."""
        code = textwrap.dedent('''\
            class MyClass:
                def __enter__(self):
                    return self
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer("MyClass")
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert transformer.converted is True
        assert result.count("def __exit__") == 1

    def test_add_missing_enter(self):
        """Should add __enter__ if only __exit__ exists."""
        code = textwrap.dedent('''\
            class MyClass:
                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer("MyClass")
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert transformer.converted is True
        assert result.count("def __enter__") == 1


# =============================================================================
# Multiple Class Tests
# =============================================================================

class TestMultipleClasses:
    """Tests with multiple classes in module."""

    def test_only_target_class_converted(self):
        """Should only convert the target class."""
        code = textwrap.dedent('''\
            class First:
                pass

            class Second:
                pass

            class Third:
                pass
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer("Second")
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert transformer.converted is True
        # Should only add methods to Second
        assert result.count("def __enter__") == 1
        assert result.count("def __exit__") == 1

    def test_nested_classes_not_affected(self):
        """Should not affect nested classes with different names."""
        code = textwrap.dedent('''\
            class Outer:
                class Inner:
                    pass
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer("Outer")
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert transformer.converted is True
        # Methods should be added to Outer
        assert "def __enter__" in result


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for context manager conversion."""

    def test_real_world_file_handler(self):
        """Test converting a realistic file handler class."""
        code = textwrap.dedent('''\
            class FileHandler:
                def __init__(self, path: str):
                    self.path = path
                    self.file = None

                def open(self):
                    self.file = open(self.path)

                def close(self):
                    if self.file:
                        self.file.close()
                        self.file = None

                def read(self) -> str:
                    return self.file.read()
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer("FileHandler")
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert transformer.converted is True
        assert "def __enter__" in result
        assert "def __exit__" in result
        assert "self.open()" in result
        assert "self.close()" in result

    def test_real_world_db_connection(self):
        """Test converting a realistic database connection class."""
        code = textwrap.dedent('''\
            class DatabaseConnection:
                def __init__(self, host: str, port: int):
                    self.host = host
                    self.port = port
                    self.connection = None

                def connect(self):
                    self.connection = create_connection(self.host, self.port)

                def disconnect(self):
                    if self.connection:
                        self.connection.close()

                def execute(self, query: str):
                    return self.connection.execute(query)
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer("DatabaseConnection")
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert transformer.converted is True
        assert "def __enter__" in result
        assert "def __exit__" in result
        assert "self.connect()" in result
        assert "self.disconnect()" in result

    def test_converted_class_usable_as_context_manager(self):
        """Converted code should be syntactically valid."""
        code = textwrap.dedent('''\
            class Resource:
                def __init__(self):
                    self.acquired = False

                def acquire(self):
                    self.acquired = True

                def release(self):
                    self.acquired = False
        ''')
        tree = cst.parse_module(code)

        transformer = ConvertToContextManagerTransformer(
            "Resource",
            enter_body="self.acquire()\nreturn self",
            exit_body="self.release()\nreturn None",
        )
        new_tree = tree.visit(transformer)
        result = new_tree.code

        # Verify the result is valid Python
        cst.parse_module(result)  # Should not raise
        assert transformer.converted is True
