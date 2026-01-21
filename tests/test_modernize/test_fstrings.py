"""
Tests for rejig.modernize.fstrings module.

This module tests f-string conversion transformers:
- FormatToFstringTransformer
- PercentToFstringTransformer
"""
from __future__ import annotations

import libcst as cst
import pytest

from rejig.modernize.fstrings import (
    FormatToFstringTransformer,
    PercentToFstringTransformer,
)


# =============================================================================
# FormatToFstringTransformer Tests
# =============================================================================

class TestFormatToFstringTransformer:
    """Tests for FormatToFstringTransformer."""

    def test_init(self):
        """Transformer should initialize with changed=False."""
        transformer = FormatToFstringTransformer()
        assert transformer.changed is False

    def test_simple_positional(self):
        """Should convert simple positional format."""
        code = '"Hello {}".format(name)'
        tree = cst.parse_expression(code)

        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)
        result = new_tree.code if hasattr(new_tree, 'code') else str(new_tree)

        assert transformer.changed is True
        assert "f\"" in result or "f'" in result
        assert "name" in result

    def test_multiple_positional(self):
        """Should convert multiple positional arguments."""
        code = '"{} + {} = {}".format(a, b, c)'
        tree = cst.parse_expression(code)

        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_indexed_positional(self):
        """Should convert indexed positional format."""
        code = '"{0} and {1}".format(first, second)'
        tree = cst.parse_expression(code)

        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_keyword_arguments(self):
        """Should convert keyword arguments."""
        code = '"Hello {name}".format(name=value)'
        tree = cst.parse_expression(code)

        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_mixed_positional_and_keyword(self):
        """Should convert mixed positional and keyword args."""
        code = '"{} is {name}".format(thing, name=value)'
        tree = cst.parse_expression(code)

        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_format_spec(self):
        """Should preserve format specifications."""
        code = '"{:.2f}".format(value)'
        tree = cst.parse_expression(code)

        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)
        result = str(new_tree)

        assert transformer.changed is True
        assert ".2f" in result

    def test_conversion_flag_s(self):
        """Should handle !s conversion."""
        code = '"{!s}".format(obj)'
        tree = cst.parse_expression(code)

        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_conversion_flag_r(self):
        """Should handle !r conversion."""
        code = '"{!r}".format(obj)'
        tree = cst.parse_expression(code)

        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_escaped_braces(self):
        """Should handle escaped braces {{ and }}."""
        code = '"{{literal}}".format()'
        tree = cst.parse_expression(code)

        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)

        # No placeholders to convert, so may not change
        # but should not raise

    def test_triple_quoted_string(self):
        """Should handle triple-quoted strings."""
        code = '"""Hello {}""".format(name)'
        tree = cst.parse_expression(code)

        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_single_quoted_string(self):
        """Should handle single-quoted strings."""
        code = "'Hello {}'.format(name)"
        tree = cst.parse_expression(code)

        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_raw_string(self):
        """Should handle raw strings."""
        code = 'r"Path: {}".format(path)'
        tree = cst.parse_expression(code)

        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = str(new_tree)
        assert "f" in result.lower()

    def test_non_format_call(self):
        """Should not modify non-format calls."""
        code = 'mystring.upper()'
        tree = cst.parse_expression(code)

        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is False

    def test_format_on_variable(self):
        """Should not convert format on variable (not literal)."""
        code = 'template.format(name)'
        tree = cst.parse_expression(code)

        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)

        # Can't convert because template is not a literal
        assert transformer.changed is False

    def test_star_args_not_converted(self):
        """Should not convert *args format calls."""
        code = '"Hello {}".format(*names)'
        tree = cst.parse_expression(code)

        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)

        # Cannot convert *args
        assert transformer.changed is False

    def test_kwargs_not_converted(self):
        """Should not convert **kwargs format calls."""
        code = '"Hello {name}".format(**data)'
        tree = cst.parse_expression(code)

        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)

        # Cannot convert **kwargs
        assert transformer.changed is False


# =============================================================================
# PercentToFstringTransformer Tests
# =============================================================================

class TestPercentToFstringTransformer:
    """Tests for PercentToFstringTransformer."""

    def test_init(self):
        """Transformer should initialize with changed=False."""
        transformer = PercentToFstringTransformer()
        assert transformer.changed is False

    def test_simple_string(self):
        """Should convert simple %s format."""
        code = '"Hello %s" % name'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_multiple_strings(self):
        """Should convert multiple %s."""
        code = '"%s and %s" % (a, b)'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_integer_format(self):
        """Should convert %d integer format."""
        code = '"Count: %d" % count'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_float_format(self):
        """Should convert %f float format."""
        code = '"Value: %f" % value'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_precision_format(self):
        """Should preserve precision in float format."""
        code = '"Value: %.2f" % value'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)
        result = str(new_tree)

        assert transformer.changed is True
        assert ".2" in result

    def test_width_format(self):
        """Should preserve width specification."""
        code = '"Value: %10s" % value'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)
        result = str(new_tree)

        assert transformer.changed is True
        assert "10" in result

    def test_repr_format(self):
        """Should convert %r repr format."""
        code = '"Object: %r" % obj'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_hex_format(self):
        """Should convert %x hex format."""
        code = '"Hex: %x" % num'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_octal_format(self):
        """Should convert %o octal format."""
        code = '"Octal: %o" % num'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_named_parameter(self):
        """Should convert named parameters."""
        code = '"Hello %(name)s" % {"name": value}'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_multiple_named_parameters(self):
        """Should convert multiple named parameters."""
        code = '"%(first)s and %(second)s" % {"first": a, "second": b}'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_percent_escape(self):
        """Should handle %% escape."""
        code = '"100%%" % ()'
        tree = cst.parse_expression(code)

        # This may not transform or may handle specially
        transformer = PercentToFstringTransformer()
        # Should not raise

    def test_left_justify_flag(self):
        """Should handle left justify flag."""
        code = '"Value: %-10s" % value'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_plus_flag(self):
        """Should handle + sign flag."""
        code = '"Value: %+d" % value'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_zero_padding_flag(self):
        """Should handle zero padding flag."""
        code = '"Value: %05d" % value'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_non_percent_modulo(self):
        """Should not modify modulo on non-string."""
        code = '10 % 3'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is False

    def test_function_call_value(self):
        """Should handle function call as value."""
        code = '"Result: %s" % get_value()'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_attribute_value(self):
        """Should handle attribute access as value."""
        code = '"Name: %s" % obj.name'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_subscript_value(self):
        """Should handle subscript as value."""
        code = '"Item: %s" % items[0]'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_dynamic_width_not_converted(self):
        """Should not convert dynamic width (*)."""
        code = '"Value: %*s" % (width, value)'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        # Cannot convert dynamic width
        assert transformer.changed is False

    def test_triple_quoted(self):
        """Should handle triple-quoted strings."""
        code = '"""Hello %s""" % name'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True

    def test_raw_string(self):
        """Should handle raw strings."""
        code = 'r"Path: %s" % path'
        tree = cst.parse_expression(code)

        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for f-string conversion."""

    def test_full_module_format_conversion(self):
        """Should convert format() calls in a full module."""
        code = '''
def greet(name):
    return "Hello {}".format(name)

def describe(obj):
    return "Type: {}, Value: {}".format(type(obj).__name__, obj)
'''
        tree = cst.parse_module(code)
        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = new_tree.code
        assert ".format" not in result
        assert "f\"" in result or "f'" in result

    def test_full_module_percent_conversion(self):
        """Should convert % formatting in a full module."""
        code = '''
def greet(name):
    return "Hello %s" % name

def format_number(n):
    return "Value: %05d" % n
'''
        tree = cst.parse_module(code)
        transformer = PercentToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
        result = new_tree.code
        assert "%" not in result or "f\"" in result or "f'" in result

    def test_unchanged_module(self):
        """Should not change module without format calls."""
        code = '''
def greet(name):
    return f"Hello {name}"

x = 10 % 3
'''
        tree = cst.parse_module(code)

        format_transformer = FormatToFstringTransformer()
        tree.visit(format_transformer)
        assert format_transformer.changed is False

    def test_complex_expressions_in_format(self):
        """Should handle complex expressions."""
        code = '"Result: {}".format(calculate(x, y) + offset)'
        tree = cst.parse_expression(code)

        transformer = FormatToFstringTransformer()
        new_tree = tree.visit(transformer)

        assert transformer.changed is True
