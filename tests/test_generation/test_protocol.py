"""
Tests for rejig.generation.protocol module.

This module tests Protocol and ABC extraction:
- ExtractProtocolTransformer
- ExtractAbstractBaseTransformer
"""
from __future__ import annotations

import textwrap

import libcst as cst
import pytest

from rejig.generation.protocol import (
    ExtractAbstractBaseTransformer,
    ExtractProtocolTransformer,
)


# =============================================================================
# ExtractProtocolTransformer Tests
# =============================================================================

class TestExtractProtocolTransformer:
    """Tests for ExtractProtocolTransformer."""

    def test_extracts_all_public_methods(self):
        """Should extract all public methods into a Protocol."""
        code = textwrap.dedent('''\
            class Service:
                def start(self):
                    pass

                def stop(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractProtocolTransformer("Service", "ServiceProtocol")
        modified = tree.visit(transformer)

        result = modified.code
        assert "class ServiceProtocol(Protocol)" in result
        assert "def start(self)" in result
        assert "def stop(self)" in result
        assert transformer.extracted is True

    def test_uses_ellipsis_body(self):
        """Protocol methods should have ... as body."""
        code = textwrap.dedent('''\
            class Handler:
                def handle(self, data: str) -> bool:
                    return True
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractProtocolTransformer("Handler", "HandlerProtocol")
        modified = tree.visit(transformer)

        result = modified.code
        assert "class HandlerProtocol(Protocol)" in result
        assert "..." in result
        assert transformer.extracted is True

    def test_extracts_specific_methods(self):
        """Should only extract specified methods."""
        code = textwrap.dedent('''\
            class Service:
                def start(self):
                    pass

                def stop(self):
                    pass

                def status(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractProtocolTransformer(
            "Service", "ServiceProtocol", methods=["start", "stop"]
        )
        modified = tree.visit(transformer)

        result = modified.code
        assert "def start" in result
        assert "def stop" in result
        # status should not be in the protocol
        assert transformer.extracted is True

    def test_skips_private_methods_by_default(self):
        """Should skip private methods (_method) by default."""
        code = textwrap.dedent('''\
            class Worker:
                def run(self):
                    pass

                def _internal(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractProtocolTransformer("Worker", "WorkerProtocol")
        modified = tree.visit(transformer)

        result = modified.code
        assert "def run" in result
        # _internal is private and should be skipped
        assert transformer.extracted is True

    def test_includes_private_methods_when_specified(self):
        """Should include private methods when explicitly listed."""
        code = textwrap.dedent('''\
            class Worker:
                def run(self):
                    pass

                def _helper(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractProtocolTransformer(
            "Worker", "WorkerProtocol", methods=["run", "_helper"]
        )
        modified = tree.visit(transformer)

        result = modified.code
        assert "def run" in result
        assert "def _helper" in result
        assert transformer.extracted is True

    def test_preserves_relevant_decorators(self):
        """Should preserve property, classmethod, staticmethod decorators."""
        code = textwrap.dedent('''\
            class Config:
                @property
                def value(self) -> int:
                    return 42

                @classmethod
                def create(cls):
                    return cls()
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractProtocolTransformer("Config", "ConfigProtocol")
        modified = tree.visit(transformer)

        result = modified.code
        assert "@property" in result
        assert "@classmethod" in result
        assert transformer.extracted is True

    def test_inserts_protocol_before_class(self):
        """Should insert Protocol class before the original class."""
        code = textwrap.dedent('''\
            class Handler:
                def handle(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractProtocolTransformer("Handler", "HandlerProtocol")
        modified = tree.visit(transformer)

        result = modified.code
        # Protocol should appear before the original class
        protocol_pos = result.find("class HandlerProtocol")
        handler_pos = result.find("class Handler:")
        assert protocol_pos < handler_pos
        assert transformer.extracted is True

    def test_no_extraction_when_no_methods(self):
        """Should not extract when class has no public methods."""
        code = textwrap.dedent('''\
            class Empty:
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractProtocolTransformer("Empty", "EmptyProtocol")
        modified = tree.visit(transformer)

        # No extraction should happen
        assert transformer.extracted is False

    def test_targets_specific_class(self):
        """Should only extract from the target class."""
        code = textwrap.dedent('''\
            class Service:
                def start(self):
                    pass

            class Worker:
                def run(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractProtocolTransformer("Service", "ServiceProtocol")
        modified = tree.visit(transformer)

        result = modified.code
        assert "class ServiceProtocol" in result
        # Worker should be unaffected
        assert "class WorkerProtocol" not in result


# =============================================================================
# ExtractAbstractBaseTransformer Tests
# =============================================================================

class TestExtractAbstractBaseTransformer:
    """Tests for ExtractAbstractBaseTransformer."""

    def test_extracts_all_public_methods_as_abstract(self):
        """Should extract public methods as abstract methods."""
        code = textwrap.dedent('''\
            class Service:
                def start(self):
                    pass

                def stop(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractAbstractBaseTransformer("Service", "AbstractService")
        modified = tree.visit(transformer)

        result = modified.code
        assert "class AbstractService(ABC)" in result
        assert "@abstractmethod" in result
        assert "def start" in result
        assert "def stop" in result
        assert transformer.extracted is True

    def test_adds_abstractmethod_decorator(self):
        """All extracted methods should have @abstractmethod."""
        code = textwrap.dedent('''\
            class Handler:
                def handle(self, data: str) -> bool:
                    return True
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractAbstractBaseTransformer("Handler", "AbstractHandler")
        modified = tree.visit(transformer)

        result = modified.code
        assert "@abstractmethod" in result
        assert transformer.extracted is True

    def test_makes_original_class_inherit_from_abc(self):
        """Original class should inherit from the new ABC."""
        code = textwrap.dedent('''\
            class Service:
                def start(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractAbstractBaseTransformer("Service", "AbstractService")
        modified = tree.visit(transformer)

        result = modified.code
        # Original class should now inherit from AbstractService
        assert "class Service(AbstractService" in result
        assert transformer.extracted is True

    def test_extracts_specific_methods(self):
        """Should only extract specified methods."""
        code = textwrap.dedent('''\
            class Worker:
                def start(self):
                    pass

                def stop(self):
                    pass

                def status(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractAbstractBaseTransformer(
            "Worker", "AbstractWorker", methods=["start", "stop"]
        )
        modified = tree.visit(transformer)

        result = modified.code
        # status should not be in the ABC
        assert transformer.extracted is True

    def test_skips_private_methods_by_default(self):
        """Should skip private methods by default."""
        code = textwrap.dedent('''\
            class Worker:
                def run(self):
                    pass

                def _internal(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractAbstractBaseTransformer("Worker", "AbstractWorker")
        modified = tree.visit(transformer)

        result = modified.code
        assert "def run" in result
        # _internal should be skipped
        assert transformer.extracted is True

    def test_skips_most_dunder_methods(self):
        """Should skip most dunder methods except __init__, __call__."""
        code = textwrap.dedent('''\
            class Thing:
                def __init__(self):
                    pass

                def __repr__(self):
                    return "Thing()"

                def do(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractAbstractBaseTransformer("Thing", "AbstractThing")
        modified = tree.visit(transformer)

        result = modified.code
        # __init__ should be included (it's an exception)
        # __repr__ should be skipped
        assert "def do" in result
        assert transformer.extracted is True

    def test_preserves_property_decorators(self):
        """Should preserve property, classmethod, staticmethod decorators."""
        code = textwrap.dedent('''\
            class Config:
                @property
                def value(self) -> int:
                    return 42

                @staticmethod
                def default():
                    return Config()
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractAbstractBaseTransformer("Config", "AbstractConfig")
        modified = tree.visit(transformer)

        result = modified.code
        # Should have both @abstractmethod and @property
        assert "@abstractmethod" in result
        assert "@property" in result or "@staticmethod" in result
        assert transformer.extracted is True

    def test_inserts_abc_before_class(self):
        """Should insert ABC class before the original class."""
        code = textwrap.dedent('''\
            class Handler:
                def handle(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractAbstractBaseTransformer("Handler", "AbstractHandler")
        modified = tree.visit(transformer)

        result = modified.code
        # ABC should appear before the original class
        abc_pos = result.find("class AbstractHandler")
        handler_pos = result.find("class Handler(")
        assert abc_pos < handler_pos
        assert transformer.extracted is True

    def test_preserves_existing_base_classes(self):
        """Should preserve existing base classes when adding ABC."""
        code = textwrap.dedent('''\
            class MyService(BaseService):
                def run(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractAbstractBaseTransformer("MyService", "AbstractMyService")
        modified = tree.visit(transformer)

        result = modified.code
        # Should have both AbstractMyService and BaseService
        assert "AbstractMyService" in result
        assert "BaseService" in result
        assert transformer.extracted is True

    def test_no_extraction_when_no_methods(self):
        """Should not extract when class has no suitable methods."""
        code = textwrap.dedent('''\
            class Empty:
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractAbstractBaseTransformer("Empty", "AbstractEmpty")
        modified = tree.visit(transformer)

        assert transformer.extracted is False


# =============================================================================
# Integration Tests
# =============================================================================

class TestProtocolIntegration:
    """Integration tests for Protocol/ABC extraction."""

    def test_protocol_and_abc_different_outputs(self):
        """Protocol and ABC should produce different outputs."""
        code = textwrap.dedent('''\
            class Service:
                def start(self):
                    pass
        ''')

        tree_protocol = cst.parse_module(code)
        tree_abc = cst.parse_module(code)

        protocol_transformer = ExtractProtocolTransformer("Service", "ServiceProtocol")
        abc_transformer = ExtractAbstractBaseTransformer("Service", "AbstractService")

        protocol_result = tree_protocol.visit(protocol_transformer).code
        abc_result = tree_abc.visit(abc_transformer).code

        # Protocol should inherit from Protocol
        assert "Protocol" in protocol_result

        # ABC should inherit from ABC and have @abstractmethod
        assert "ABC" in abc_result
        assert "@abstractmethod" in abc_result

    def test_extracted_protocol_is_valid_python(self):
        """Extracted protocol should be valid Python code."""
        code = textwrap.dedent('''\
            class Handler:
                def handle(self, data: str) -> bool:
                    return True

                def close(self) -> None:
                    pass
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractProtocolTransformer("Handler", "HandlerProtocol")
        modified = tree.visit(transformer)

        # Should parse without error
        result = modified.code
        cst.parse_module(result)  # Should not raise
        assert transformer.extracted is True

    def test_extracted_abc_is_valid_python(self):
        """Extracted ABC should be valid Python code."""
        code = textwrap.dedent('''\
            class Worker:
                def run(self) -> None:
                    pass

                def stop(self) -> None:
                    pass
        ''')

        tree = cst.parse_module(code)
        transformer = ExtractAbstractBaseTransformer("Worker", "AbstractWorker")
        modified = tree.visit(transformer)

        # Should parse without error
        result = modified.code
        cst.parse_module(result)  # Should not raise
        assert transformer.extracted is True
