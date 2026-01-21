"""
Tests for rejig.modernize.python2 module.

This module tests Python 2 compatibility removal:
- RemovePython2CompatTransformer
- AddFutureAnnotationsTransformer
- RemoveSixUsageTransformer
"""
from __future__ import annotations

import textwrap

import libcst as cst
import pytest

from rejig.modernize.python2 import (
    AddFutureAnnotationsTransformer,
    RemovePython2CompatTransformer,
    RemoveSixUsageTransformer,
)


def _expr_to_code(expr: cst.BaseExpression) -> str:
    """Convert a CST expression to code string."""
    module = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=expr)])])
    return module.code.strip()


# =============================================================================
# RemovePython2CompatTransformer Tests
# =============================================================================

class TestRemovePython2CompatTransformer:
    """Tests for RemovePython2CompatTransformer."""

    def test_init(self):
        """Transformer should initialize with changed=False."""
        transformer = RemovePython2CompatTransformer()
        assert transformer.changed is False

    # -------------------------------------------------------------------------
    # __future__ Import Removal
    # -------------------------------------------------------------------------

    def test_remove_print_function_import(self):
        """Should remove print_function future import."""
        code = "from __future__ import print_function"
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        assert "print_function" not in new_tree.code

    def test_remove_division_import(self):
        """Should remove division future import."""
        code = "from __future__ import division"
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        assert "division" not in new_tree.code

    def test_remove_absolute_import(self):
        """Should remove absolute_import future import."""
        code = "from __future__ import absolute_import"
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        assert "absolute_import" not in new_tree.code

    def test_remove_unicode_literals_import(self):
        """Should remove unicode_literals future import."""
        code = "from __future__ import unicode_literals"
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        assert "unicode_literals" not in new_tree.code

    def test_keep_annotations_import(self):
        """Should keep annotations future import."""
        code = "from __future__ import annotations"
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert "annotations" in new_tree.code

    def test_remove_multiple_future_imports(self):
        """Should remove multiple Python 2 future imports."""
        code = "from __future__ import print_function, division, absolute_import"
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = new_tree.code
        assert "print_function" not in result
        assert "division" not in result
        assert "absolute_import" not in result

    def test_keep_annotations_remove_others(self):
        """Should keep annotations but remove other Python 2 imports."""
        code = "from __future__ import annotations, print_function"
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = new_tree.code
        assert "annotations" in result
        assert "print_function" not in result

    # -------------------------------------------------------------------------
    # super() Conversion
    # -------------------------------------------------------------------------

    def test_convert_super_with_class_self(self):
        """Should convert super(ClassName, self) to super()."""
        code = textwrap.dedent('''\
            class MyClass:
                def method(self):
                    super(MyClass, self).method()
        ''')
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = new_tree.code
        assert "super()" in result
        assert "super(MyClass, self)" not in result

    def test_convert_super_with_cls(self):
        """Should convert super(ClassName, cls) to super()."""
        code = textwrap.dedent('''\
            class MyClass:
                @classmethod
                def method(cls):
                    super(MyClass, cls).method()
        ''')
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        assert "super()" in new_tree.code

    def test_keep_super_with_different_args(self):
        """Should not change super() with other arguments."""
        code = textwrap.dedent('''\
            class MyClass:
                def method(self):
                    super(OtherClass, other_obj).method()
        ''')
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        # Should not change since second arg is not self/cls
        assert "super(OtherClass, other_obj)" in new_tree.code

    def test_keep_zero_arg_super(self):
        """Should not change super() with no arguments."""
        code = textwrap.dedent('''\
            class MyClass:
                def method(self):
                    super().method()
        ''')
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert "super()" in new_tree.code

    # -------------------------------------------------------------------------
    # Unicode String Prefix Removal
    # -------------------------------------------------------------------------

    def test_remove_u_prefix_double_quote(self):
        """Should remove u prefix from double-quoted strings."""
        code = 'x = u"hello"'
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        assert 'u"' not in new_tree.code
        assert '"hello"' in new_tree.code

    def test_remove_u_prefix_single_quote(self):
        """Should remove u prefix from single-quoted strings."""
        code = "x = u'hello'"
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        assert "u'" not in new_tree.code

    def test_remove_upper_u_prefix(self):
        """Should remove U prefix from strings."""
        code = 'x = U"hello"'
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        assert 'U"' not in new_tree.code

    @pytest.mark.skip(reason="ur prefix is invalid syntax in Python 3")
    def test_convert_ur_prefix_to_r(self):
        """Should convert ur prefix to r prefix."""
        # Note: This test cannot run in Python 3 because ur"" is invalid syntax
        # The implementation handles this for Python 2 code migration
        pass

    # -------------------------------------------------------------------------
    # object Base Class Removal
    # -------------------------------------------------------------------------

    def test_remove_object_base_class(self):
        """Should remove object when it's the only base class."""
        code = "class MyClass(object): pass"
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = new_tree.code
        assert "(object)" not in result
        assert "class MyClass:" in result or "class MyClass\n" in result

    def test_keep_object_with_other_bases(self):
        """Should keep object when there are other base classes."""
        code = "class MyClass(object, Mixin): pass"
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        # Should not change since there are multiple bases
        assert "object" in new_tree.code
        assert "Mixin" in new_tree.code

    def test_keep_non_object_base(self):
        """Should keep other base classes."""
        code = "class MyClass(BaseClass): pass"
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert "BaseClass" in new_tree.code

    # -------------------------------------------------------------------------
    # Coding Comment Removal
    # -------------------------------------------------------------------------

    def test_remove_coding_comment_utf8(self):
        """Should remove UTF-8 coding comment."""
        code = "# -*- coding: utf-8 -*-\nx = 1"
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        assert "coding" not in new_tree.code

    def test_remove_coding_comment_simple(self):
        """Should remove simple coding comment."""
        code = "# coding: utf-8\nx = 1"
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        assert "coding" not in new_tree.code

    def test_keep_non_coding_comment(self):
        """Should keep other comments."""
        code = "# This is a regular comment\nx = 1"
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        assert "regular comment" in new_tree.code


# =============================================================================
# AddFutureAnnotationsTransformer Tests
# =============================================================================

class TestAddFutureAnnotationsTransformer:
    """Tests for AddFutureAnnotationsTransformer."""

    def test_init(self):
        """Transformer should initialize with added=False."""
        transformer = AddFutureAnnotationsTransformer()
        assert transformer.added is False

    def test_add_annotations_to_empty_module(self):
        """Should add annotations import to empty module."""
        code = "x = 1"
        tree = cst.parse_module(code)

        transformer = AddFutureAnnotationsTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.added is True
        result = new_tree.code
        assert "from __future__ import annotations" in result

    def test_add_annotations_after_docstring(self):
        """Should add annotations after module docstring."""
        code = textwrap.dedent('''\
            """Module docstring."""
            x = 1
        ''')
        tree = cst.parse_module(code)

        transformer = AddFutureAnnotationsTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.added is True
        result = new_tree.code
        lines = result.strip().split('\n')
        # Docstring should still be first
        assert '"""' in lines[0]
        # Annotations should be somewhere after
        assert "from __future__ import annotations" in result

    def test_skip_if_annotations_exists(self):
        """Should not add if annotations already imported."""
        code = textwrap.dedent('''\
            from __future__ import annotations
            x = 1
        ''')
        tree = cst.parse_module(code)

        transformer = AddFutureAnnotationsTransformer()
        new_tree = tree.visit(transformer)

        # Should not add duplicate
        assert new_tree.code.count("annotations") == 1

    def test_add_to_existing_future_import(self):
        """Should add annotations to existing __future__ import."""
        code = "from __future__ import division\nx = 1"
        tree = cst.parse_module(code)

        transformer = AddFutureAnnotationsTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.added is True
        result = new_tree.code
        assert "annotations" in result


# =============================================================================
# RemoveSixUsageTransformer Tests
# =============================================================================

class TestRemoveSixUsageTransformer:
    """Tests for RemoveSixUsageTransformer."""

    def test_init(self):
        """Transformer should initialize with changed=False."""
        transformer = RemoveSixUsageTransformer()
        assert transformer.changed is False

    # -------------------------------------------------------------------------
    # six.text_type and similar
    # -------------------------------------------------------------------------

    def test_replace_six_text_type(self):
        """Should replace six.text_type with str."""
        code = "six.text_type"
        tree = cst.parse_expression(code)

        transformer = RemoveSixUsageTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = _expr_to_code(new_tree)
        assert result == "str"

    def test_replace_six_binary_type(self):
        """Should replace six.binary_type with bytes."""
        code = "six.binary_type"
        tree = cst.parse_expression(code)

        transformer = RemoveSixUsageTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = _expr_to_code(new_tree)
        assert result == "bytes"

    def test_replace_six_string_types(self):
        """Should replace six.string_types with str."""
        code = "six.string_types"
        tree = cst.parse_expression(code)

        transformer = RemoveSixUsageTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = _expr_to_code(new_tree)
        assert result == "str"

    def test_replace_six_integer_types(self):
        """Should replace six.integer_types with int."""
        code = "six.integer_types"
        tree = cst.parse_expression(code)

        transformer = RemoveSixUsageTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = _expr_to_code(new_tree)
        assert result == "int"

    # -------------------------------------------------------------------------
    # six.PY2 and six.PY3
    # -------------------------------------------------------------------------

    def test_replace_six_py2(self):
        """Should replace six.PY2 with False."""
        code = "six.PY2"
        tree = cst.parse_expression(code)

        transformer = RemoveSixUsageTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = _expr_to_code(new_tree)
        assert result == "False"

    def test_replace_six_py3(self):
        """Should replace six.PY3 with True."""
        code = "six.PY3"
        tree = cst.parse_expression(code)

        transformer = RemoveSixUsageTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = _expr_to_code(new_tree)
        assert result == "True"

    # -------------------------------------------------------------------------
    # six.moves
    # -------------------------------------------------------------------------

    def test_replace_six_moves_range(self):
        """Should replace six.moves.range with range."""
        code = "six.moves.range"
        tree = cst.parse_expression(code)

        transformer = RemoveSixUsageTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = _expr_to_code(new_tree)
        assert result == "range"

    def test_replace_six_moves_map(self):
        """Should replace six.moves.map with map."""
        code = "six.moves.map"
        tree = cst.parse_expression(code)

        transformer = RemoveSixUsageTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = _expr_to_code(new_tree)
        assert result == "map"

    def test_replace_six_moves_filter(self):
        """Should replace six.moves.filter with filter."""
        code = "six.moves.filter"
        tree = cst.parse_expression(code)

        transformer = RemoveSixUsageTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = _expr_to_code(new_tree)
        assert result == "filter"

    def test_replace_six_moves_zip(self):
        """Should replace six.moves.zip with zip."""
        code = "six.moves.zip"
        tree = cst.parse_expression(code)

        transformer = RemoveSixUsageTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = _expr_to_code(new_tree)
        assert result == "zip"

    def test_replace_six_moves_input(self):
        """Should replace six.moves.input with input."""
        code = "six.moves.input"
        tree = cst.parse_expression(code)

        transformer = RemoveSixUsageTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = _expr_to_code(new_tree)
        assert result == "input"


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for Python 2 removal."""

    def test_full_python2_removal(self):
        """Should remove all Python 2 compatibility from a module."""
        code = textwrap.dedent('''\
            # -*- coding: utf-8 -*-
            from __future__ import print_function, division

            class MyClass(object):
                def __init__(self):
                    super(MyClass, self).__init__()
                    self.name = u"test"
        ''')
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)
        result = new_tree.code

        assert transformer.changed is True
        assert "coding" not in result
        assert "print_function" not in result
        assert "division" not in result
        assert "(object)" not in result
        assert "super()" in result
        assert 'u"' not in result

    def test_mixed_six_and_python2_compat(self):
        """Should handle both six and Python 2 compat."""
        code = textwrap.dedent('''\
            from __future__ import print_function

            class MyClass(object):
                def check(self, x):
                    return isinstance(x, six.string_types)
        ''')
        tree = cst.parse_module(code)

        # First remove Python 2 compat
        py2_transformer = RemovePython2CompatTransformer()
        tree = tree.visit(py2_transformer)

        # Then remove six usage
        six_transformer = RemoveSixUsageTransformer()
        tree = tree.visit(six_transformer)

        result = tree.code
        assert "print_function" not in result
        assert "(object)" not in result
        assert "six.string_types" not in result
        assert "str" in result

    def test_preserve_valid_modern_code(self):
        """Should not change valid modern Python code."""
        code = textwrap.dedent('''\
            from __future__ import annotations

            class MyClass:
                def __init__(self):
                    super().__init__()
                    self.name = "test"
        ''')
        tree = cst.parse_module(code)

        transformer = RemovePython2CompatTransformer()
        new_tree = tree.visit(transformer)

        # Should not change (nothing to remove)
        # annotations should be preserved
        assert "annotations" in new_tree.code
        assert "super()" in new_tree.code
