"""
Tests for rejig.typehints.modernizer module.

This module tests TypeHintModernizer for modernizing type hints:
- Converting List[str] → list[str]
- Converting Dict[str, int] → dict[str, int]
- Converting Optional[str] → str | None
- Converting Union[str, int] → str | int
- TypeCommentConverter for type: comments

TypeHintModernizer transforms old-style type hints to Python 3.10+ syntax.

Coverage targets:
- Built-in generics conversion (List, Dict, Set, etc.)
- Optional to union None conversion
- Union to pipe syntax conversion
- Nested type handling
- Type comment conversion
"""
from __future__ import annotations

import textwrap

import libcst as cst
import pytest

from rejig.typehints import TypeHintModernizer, TypeCommentConverter


# =============================================================================
# TypeHintModernizer Builtin Generics Tests
# =============================================================================

class TestTypeHintModernizerBuiltins:
    """Tests for converting typing module generics to builtins."""

    def test_list_to_builtin(self):
        """
        TypeHintModernizer should convert List[str] to list[str].
        """
        code = "from typing import List\nx: List[str] = []"

        tree = cst.parse_module(code)
        modernizer = TypeHintModernizer()
        new_tree = tree.visit(modernizer)

        result = new_tree.code
        assert "list[str]" in result
        assert modernizer.changed is True

    def test_dict_to_builtin(self):
        """
        TypeHintModernizer should convert Dict[str, int] to dict[str, int].
        """
        code = "from typing import Dict\nx: Dict[str, int] = {}"

        tree = cst.parse_module(code)
        modernizer = TypeHintModernizer()
        new_tree = tree.visit(modernizer)

        result = new_tree.code
        assert "dict[str, int]" in result
        assert modernizer.changed is True

    def test_set_to_builtin(self):
        """
        TypeHintModernizer should convert Set[int] to set[int].
        """
        code = "from typing import Set\nx: Set[int] = set()"

        tree = cst.parse_module(code)
        modernizer = TypeHintModernizer()
        new_tree = tree.visit(modernizer)

        result = new_tree.code
        assert "set[int]" in result

    def test_tuple_to_builtin(self):
        """
        TypeHintModernizer should convert Tuple[int, str] to tuple[int, str].
        """
        code = "from typing import Tuple\nx: Tuple[int, str] = (1, 'a')"

        tree = cst.parse_module(code)
        modernizer = TypeHintModernizer()
        new_tree = tree.visit(modernizer)

        result = new_tree.code
        assert "tuple[int, str]" in result

    def test_frozenset_to_builtin(self):
        """
        TypeHintModernizer should convert FrozenSet[str] to frozenset[str].
        """
        code = "from typing import FrozenSet\nx: FrozenSet[str] = frozenset()"

        tree = cst.parse_module(code)
        modernizer = TypeHintModernizer()
        new_tree = tree.visit(modernizer)

        result = new_tree.code
        assert "frozenset[str]" in result

    def test_type_to_builtin(self):
        """
        TypeHintModernizer should convert Type[T] to type[T].
        """
        code = "from typing import Type\nx: Type[MyClass] = MyClass"

        tree = cst.parse_module(code)
        modernizer = TypeHintModernizer()
        new_tree = tree.visit(modernizer)

        result = new_tree.code
        assert "type[MyClass]" in result


# =============================================================================
# TypeHintModernizer Optional Tests
# =============================================================================

class TestTypeHintModernizerOptional:
    """Tests for converting Optional to union with None."""

    def test_optional_to_pipe_none(self):
        """
        TypeHintModernizer should convert Optional[str] to str | None.
        """
        code = "from typing import Optional\nx: Optional[str] = None"

        tree = cst.parse_module(code)
        modernizer = TypeHintModernizer()
        new_tree = tree.visit(modernizer)

        result = new_tree.code
        # Should have pipe syntax
        assert "| None" in result or "|None" in result
        assert "Optional" not in result.split("\n")[-1]  # Not in the variable line
        assert modernizer.changed is True

    def test_optional_with_complex_type(self):
        """
        TypeHintModernizer should handle Optional with complex inner types.
        """
        code = "from typing import Optional, List\nx: Optional[List[str]] = None"

        tree = cst.parse_module(code)
        modernizer = TypeHintModernizer()
        new_tree = tree.visit(modernizer)

        result = new_tree.code
        # The inner List should also be converted
        assert "| None" in result or "|None" in result


# =============================================================================
# TypeHintModernizer Union Tests
# =============================================================================

class TestTypeHintModernizerUnion:
    """Tests for converting Union to pipe syntax."""

    def test_union_two_types(self):
        """
        TypeHintModernizer should convert Union[str, int] to str | int.
        """
        code = "from typing import Union\nx: Union[str, int] = 'test'"

        tree = cst.parse_module(code)
        modernizer = TypeHintModernizer()
        new_tree = tree.visit(modernizer)

        result = new_tree.code
        # Should have pipe syntax between str and int
        assert "|" in result
        assert modernizer.changed is True

    def test_union_three_types(self):
        """
        TypeHintModernizer should handle Union with multiple types.
        """
        code = "from typing import Union\nx: Union[str, int, float] = 1"

        tree = cst.parse_module(code)
        modernizer = TypeHintModernizer()
        new_tree = tree.visit(modernizer)

        result = new_tree.code
        # Should have multiple pipe separators
        assert result.count("|") >= 2

    def test_union_with_none(self):
        """
        TypeHintModernizer should handle Union[str, None] (equivalent to Optional).
        """
        code = "from typing import Union\nx: Union[str, None] = None"

        tree = cst.parse_module(code)
        modernizer = TypeHintModernizer()
        new_tree = tree.visit(modernizer)

        result = new_tree.code
        assert "|" in result


# =============================================================================
# TypeHintModernizer Nested Types Tests
# =============================================================================

class TestTypeHintModernizerNested:
    """Tests for nested type conversions."""

    def test_nested_list_dict(self):
        """
        TypeHintModernizer should handle nested generics.
        """
        code = "from typing import List, Dict\nx: List[Dict[str, int]] = []"

        tree = cst.parse_module(code)
        modernizer = TypeHintModernizer()
        new_tree = tree.visit(modernizer)

        result = new_tree.code
        # Both should be converted to builtins
        assert "list[" in result
        assert "dict[" in result

    def test_optional_in_list(self):
        """
        TypeHintModernizer should handle Optional inside List.
        """
        code = "from typing import List, Optional\nx: List[Optional[str]] = []"

        tree = cst.parse_module(code)
        modernizer = TypeHintModernizer()
        new_tree = tree.visit(modernizer)

        result = new_tree.code
        assert "list[" in result


# =============================================================================
# TypeHintModernizer No Change Tests
# =============================================================================

class TestTypeHintModernizerNoChange:
    """Tests for cases where no changes should be made."""

    def test_no_change_for_modern_types(self):
        """
        TypeHintModernizer should not change already-modern types.
        """
        code = "x: list[str] = []"

        tree = cst.parse_module(code)
        modernizer = TypeHintModernizer()
        new_tree = tree.visit(modernizer)

        result = new_tree.code
        assert result.strip() == code.strip()
        assert modernizer.changed is False

    def test_no_change_for_non_typing_subscript(self):
        """
        TypeHintModernizer should not change non-typing subscripts.
        """
        code = "x = my_dict['key']"

        tree = cst.parse_module(code)
        modernizer = TypeHintModernizer()
        new_tree = tree.visit(modernizer)

        result = new_tree.code
        assert result.strip() == code.strip()


# =============================================================================
# TypeCommentConverter Tests
# =============================================================================

class TestTypeCommentConverter:
    """Tests for TypeCommentConverter."""

    def test_simple_type_comment(self):
        """
        TypeCommentConverter should convert simple type comments to annotations.

        # type: str → : str
        """
        code = textwrap.dedent('''\
            x = "hello"  # type: str
        ''')

        tree = cst.parse_module(code)
        converter = TypeCommentConverter()
        new_tree = tree.visit(converter)

        result = new_tree.code
        # Should have annotation
        assert "x: str" in result or "x:" in result

    def test_preserves_code_without_type_comments(self):
        """
        TypeCommentConverter should not change code without type comments.
        """
        code = "x: str = 'hello'"

        tree = cst.parse_module(code)
        converter = TypeCommentConverter()
        new_tree = tree.visit(converter)

        result = new_tree.code
        assert result.strip() == code.strip()


# =============================================================================
# Integration Tests
# =============================================================================

class TestTypeHintModernizerIntegration:
    """Integration tests for TypeHintModernizer."""

    def test_function_parameters(self):
        """
        TypeHintModernizer should convert types in function parameters.
        """
        code = textwrap.dedent('''\
            from typing import List, Optional

            def process(items: List[str], name: Optional[str] = None) -> List[int]:
                return []
        ''')

        tree = cst.parse_module(code)
        modernizer = TypeHintModernizer()
        new_tree = tree.visit(modernizer)

        result = new_tree.code
        # Parameters should be converted
        assert "list[str]" in result
        # Return type should be converted
        assert "list[int]" in result or "-> list" in result

    def test_class_attributes(self):
        """
        TypeHintModernizer should convert types in class attributes.
        """
        code = textwrap.dedent('''\
            from typing import Dict

            class MyClass:
                data: Dict[str, int]
        ''')

        tree = cst.parse_module(code)
        modernizer = TypeHintModernizer()
        new_tree = tree.visit(modernizer)

        result = new_tree.code
        assert "dict[str, int]" in result
