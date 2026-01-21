"""
Tests for rejig.typehints.inference module.

This module tests type inference utilities:
- TypeInference class
- infer_from_default() method
- infer_from_name() method
- infer_type() method
"""
from __future__ import annotations

import libcst as cst
import pytest

from rejig.typehints.inference import TypeInference


# =============================================================================
# Helper Functions
# =============================================================================

def parse_expr(code: str) -> cst.BaseExpression:
    """Parse a Python expression string into a CST node."""
    module = cst.parse_module(f"x = {code}")
    assign = module.body[0]
    assert isinstance(assign, cst.SimpleStatementLine)
    stmt = assign.body[0]
    assert isinstance(stmt, cst.Assign)
    return stmt.value


# =============================================================================
# TypeInference.infer_from_default Tests
# =============================================================================

class TestInferFromDefault:
    """Tests for TypeInference.infer_from_default."""

    def test_integer(self):
        """Should infer int from integer literals."""
        expr = parse_expr("42")
        assert TypeInference.infer_from_default(expr) == "int"

    def test_negative_integer(self):
        """Should infer int from negative integers."""
        expr = parse_expr("-42")
        assert TypeInference.infer_from_default(expr) == "int"

    def test_float(self):
        """Should infer float from float literals."""
        expr = parse_expr("3.14")
        assert TypeInference.infer_from_default(expr) == "float"

    def test_negative_float(self):
        """Should infer float from negative floats."""
        expr = parse_expr("-3.14")
        assert TypeInference.infer_from_default(expr) == "float"

    def test_simple_string(self):
        """Should infer str from simple string literals."""
        expr = parse_expr('"hello"')
        assert TypeInference.infer_from_default(expr) == "str"

    def test_single_quoted_string(self):
        """Should infer str from single-quoted strings."""
        expr = parse_expr("'hello'")
        assert TypeInference.infer_from_default(expr) == "str"

    def test_bytes_literal(self):
        """Should infer bytes from bytes literals."""
        expr = parse_expr('b"hello"')
        assert TypeInference.infer_from_default(expr) == "bytes"

    def test_bytes_literal_single_quote(self):
        """Should infer bytes from single-quoted bytes."""
        expr = parse_expr("b'hello'")
        assert TypeInference.infer_from_default(expr) == "bytes"

    def test_bytes_literal_uppercase(self):
        """Should infer bytes from uppercase B prefix."""
        expr = parse_expr('B"hello"')
        assert TypeInference.infer_from_default(expr) == "bytes"

    def test_true_boolean(self):
        """Should infer bool from True."""
        expr = parse_expr("True")
        assert TypeInference.infer_from_default(expr) == "bool"

    def test_false_boolean(self):
        """Should infer bool from False."""
        expr = parse_expr("False")
        assert TypeInference.infer_from_default(expr) == "bool"

    def test_none(self):
        """Should infer None from None."""
        expr = parse_expr("None")
        assert TypeInference.infer_from_default(expr) == "None"

    def test_empty_list(self):
        """Should infer list from empty list."""
        expr = parse_expr("[]")
        assert TypeInference.infer_from_default(expr) == "list"

    def test_list_with_int_elements(self):
        """Should infer list[int] from list with integers."""
        expr = parse_expr("[1, 2, 3]")
        assert TypeInference.infer_from_default(expr) == "list[int]"

    def test_list_with_str_elements(self):
        """Should infer list[str] from list with strings."""
        expr = parse_expr('["a", "b"]')
        assert TypeInference.infer_from_default(expr) == "list[str]"

    def test_empty_tuple(self):
        """Should infer tuple from empty tuple."""
        expr = parse_expr("()")
        assert TypeInference.infer_from_default(expr) == "tuple"

    def test_non_empty_tuple(self):
        """Should infer tuple from non-empty tuple."""
        expr = parse_expr("(1, 2)")
        assert TypeInference.infer_from_default(expr) == "tuple"

    def test_empty_dict(self):
        """Should infer dict from empty dict."""
        expr = parse_expr("{}")
        assert TypeInference.infer_from_default(expr) == "dict"

    def test_dict_with_typed_elements(self):
        """Should infer dict[str, int] from dict with typed elements."""
        expr = parse_expr('{"a": 1}')
        assert TypeInference.infer_from_default(expr) == "dict[str, int]"

    def test_empty_set(self):
        """Should infer set from set constructor call."""
        # Empty set literal not possible, use set()
        expr = parse_expr("set()")
        assert TypeInference.infer_from_default(expr) == "set"

    def test_set_with_elements(self):
        """Should infer set[int] from set with integers."""
        expr = parse_expr("{1, 2, 3}")
        assert TypeInference.infer_from_default(expr) == "set[int]"

    def test_list_constructor(self):
        """Should infer list from list() call."""
        expr = parse_expr("list()")
        assert TypeInference.infer_from_default(expr) == "list"

    def test_dict_constructor(self):
        """Should infer dict from dict() call."""
        expr = parse_expr("dict()")
        assert TypeInference.infer_from_default(expr) == "dict"

    def test_tuple_constructor(self):
        """Should infer tuple from tuple() call."""
        expr = parse_expr("tuple()")
        assert TypeInference.infer_from_default(expr) == "tuple"

    def test_frozenset_constructor(self):
        """Should infer frozenset from frozenset() call."""
        expr = parse_expr("frozenset()")
        assert TypeInference.infer_from_default(expr) == "frozenset"

    def test_path_constructor(self):
        """Should infer Path from Path() call."""
        expr = parse_expr('Path(".")')
        assert TypeInference.infer_from_default(expr) == "Path"

    def test_datetime_constructor(self):
        """Should infer datetime from datetime() call."""
        expr = parse_expr("datetime(2023, 1, 1)")
        assert TypeInference.infer_from_default(expr) == "datetime"

    def test_date_constructor(self):
        """Should infer date from date() call."""
        expr = parse_expr("date(2023, 1, 1)")
        assert TypeInference.infer_from_default(expr) == "date"

    def test_time_constructor(self):
        """Should infer time from time() call."""
        expr = parse_expr("time(12, 0)")
        assert TypeInference.infer_from_default(expr) == "time"

    def test_timedelta_constructor(self):
        """Should infer timedelta from timedelta() call."""
        expr = parse_expr("timedelta(days=1)")
        assert TypeInference.infer_from_default(expr) == "timedelta"

    def test_datetime_now(self):
        """Should infer datetime from datetime.now() call."""
        expr = parse_expr("datetime.now()")
        assert TypeInference.infer_from_default(expr) == "datetime"

    def test_datetime_utcnow(self):
        """Should infer datetime from datetime.utcnow() call."""
        expr = parse_expr("datetime.utcnow()")
        assert TypeInference.infer_from_default(expr) == "datetime"

    def test_datetime_today(self):
        """Should infer datetime from datetime.today() call."""
        expr = parse_expr("datetime.today()")
        assert TypeInference.infer_from_default(expr) == "datetime"

    def test_date_today(self):
        """Should infer date from date.today() call."""
        expr = parse_expr("date.today()")
        assert TypeInference.infer_from_default(expr) == "date"

    def test_lambda(self):
        """Should infer Callable from lambda."""
        expr = parse_expr("lambda x: x + 1")
        assert TypeInference.infer_from_default(expr) == "Callable"

    def test_unknown_name(self):
        """Should return None for unknown name references."""
        expr = parse_expr("some_variable")
        assert TypeInference.infer_from_default(expr) is None

    def test_unknown_call(self):
        """Should return None for unknown function calls."""
        expr = parse_expr("SomeClass()")
        assert TypeInference.infer_from_default(expr) is None


# =============================================================================
# TypeInference.infer_from_name Tests
# =============================================================================

class TestInferFromName:
    """Tests for TypeInference.infer_from_name."""

    # Integer patterns
    def test_count(self):
        """Should infer int from 'count'."""
        assert TypeInference.infer_from_name("count") == "int"

    def test_size(self):
        """Should infer int from 'size'."""
        assert TypeInference.infer_from_name("size") == "int"

    def test_index(self):
        """Should infer int from 'index'."""
        assert TypeInference.infer_from_name("index") == "int"

    def test_total(self):
        """Should infer int from 'total'."""
        assert TypeInference.infer_from_name("total") == "int"

    def test_id(self):
        """Should infer int from 'id'."""
        assert TypeInference.infer_from_name("id") == "int"

    def test_id_suffix(self):
        """Should infer int from names ending with '_id'."""
        assert TypeInference.infer_from_name("user_id") == "int"

    def test_idx_suffix(self):
        """Should infer int from names ending with '_idx'."""
        assert TypeInference.infer_from_name("start_idx") == "int"

    def test_count_suffix(self):
        """Should infer int from names ending with '_count'."""
        assert TypeInference.infer_from_name("item_count") == "int"

    def test_num_suffix(self):
        """Should infer int from names ending with '_num'."""
        assert TypeInference.infer_from_name("page_num") == "int"

    # Float patterns
    def test_price(self):
        """Should infer float from 'price'."""
        assert TypeInference.infer_from_name("price") == "float"

    def test_amount(self):
        """Should infer float from 'amount'."""
        assert TypeInference.infer_from_name("amount") == "float"

    def test_rate(self):
        """Should infer float from 'rate'."""
        assert TypeInference.infer_from_name("rate") == "float"

    def test_score(self):
        """Should infer float from 'score'."""
        assert TypeInference.infer_from_name("score") == "float"

    # String patterns
    def test_name(self):
        """Should infer str from 'name'."""
        assert TypeInference.infer_from_name("name") == "str"

    def test_title(self):
        """Should infer str from 'title'."""
        assert TypeInference.infer_from_name("title") == "str"

    def test_message(self):
        """Should infer str from 'message'."""
        assert TypeInference.infer_from_name("message") == "str"

    def test_url(self):
        """Should infer str from 'url'."""
        assert TypeInference.infer_from_name("url") == "str"

    def test_name_suffix(self):
        """Should infer str from names ending with '_name'."""
        assert TypeInference.infer_from_name("user_name") == "str"

    def test_text_suffix(self):
        """Should infer str from names ending with '_text'."""
        assert TypeInference.infer_from_name("body_text") == "str"

    def test_url_suffix(self):
        """Should infer str from names ending with '_url'."""
        assert TypeInference.infer_from_name("image_url") == "str"

    def test_uri_suffix(self):
        """Should infer str from names ending with '_uri'."""
        assert TypeInference.infer_from_name("resource_uri") == "str"

    # Path pattern
    def test_path(self):
        """Should infer str | Path from 'path'."""
        assert TypeInference.infer_from_name("path") == "str | Path"

    def test_path_suffix(self):
        """Should infer str | Path from names ending with '_path'."""
        assert TypeInference.infer_from_name("file_path") == "str | Path"

    # Bytes pattern
    def test_data(self):
        """Should infer bytes from 'data'."""
        assert TypeInference.infer_from_name("data") == "bytes"

    # Boolean patterns
    def test_enabled(self):
        """Should infer bool from 'enabled'."""
        assert TypeInference.infer_from_name("enabled") == "bool"

    def test_active(self):
        """Should infer bool from 'active'."""
        assert TypeInference.infer_from_name("active") == "bool"

    def test_valid(self):
        """Should infer bool from 'valid'."""
        assert TypeInference.infer_from_name("valid") == "bool"

    def test_is_prefix(self):
        """Should infer bool from 'is_' prefix."""
        assert TypeInference.infer_from_name("is_active") == "bool"

    def test_has_prefix(self):
        """Should infer bool from 'has_' prefix."""
        assert TypeInference.infer_from_name("has_permission") == "bool"

    def test_can_prefix(self):
        """Should infer bool from 'can_' prefix."""
        assert TypeInference.infer_from_name("can_edit") == "bool"

    def test_should_prefix(self):
        """Should infer bool from 'should_' prefix."""
        assert TypeInference.infer_from_name("should_validate") == "bool"

    def test_enabled_suffix(self):
        """Should infer bool from names ending with '_enabled'."""
        assert TypeInference.infer_from_name("feature_enabled") == "bool"

    def test_active_suffix(self):
        """Should infer bool from names ending with '_active'."""
        assert TypeInference.infer_from_name("user_active") == "bool"

    # List patterns
    def test_items(self):
        """Should infer list from 'items'."""
        assert TypeInference.infer_from_name("items") == "list"

    def test_values(self):
        """Should infer list from 'values'."""
        assert TypeInference.infer_from_name("values") == "list"

    def test_results(self):
        """Should infer list from 'results'."""
        assert TypeInference.infer_from_name("results") == "list"

    def test_list_suffix(self):
        """Should infer list from names ending with '_list'."""
        assert TypeInference.infer_from_name("user_list") == "list"

    def test_items_suffix(self):
        """Should infer list from names ending with '_items'."""
        assert TypeInference.infer_from_name("menu_items") == "list"

    # Dict patterns
    def test_mapping(self):
        """Should infer dict from 'mapping'."""
        assert TypeInference.infer_from_name("mapping") == "dict"

    def test_config(self):
        """Should infer dict from 'config'."""
        assert TypeInference.infer_from_name("config") == "dict"

    def test_kwargs(self):
        """Should infer dict from 'kwargs'."""
        assert TypeInference.infer_from_name("kwargs") == "dict"

    def test_dict_suffix(self):
        """Should infer dict from names ending with '_dict'."""
        assert TypeInference.infer_from_name("user_dict") == "dict"

    def test_map_suffix(self):
        """Should infer dict from names ending with '_map'."""
        assert TypeInference.infer_from_name("id_map") == "dict"

    # Set pattern
    def test_set_suffix(self):
        """Should infer set from names ending with '_set'."""
        assert TypeInference.infer_from_name("seen_set") == "set"

    # Tuple pattern
    def test_args(self):
        """Should infer tuple from 'args'."""
        assert TypeInference.infer_from_name("args") == "tuple"

    # Callable patterns
    def test_callback(self):
        """Should infer Callable from 'callback'."""
        assert TypeInference.infer_from_name("callback") == "Callable"

    def test_handler(self):
        """Should infer Callable from 'handler'."""
        assert TypeInference.infer_from_name("handler") == "Callable"

    def test_func(self):
        """Should infer Callable from 'func'."""
        assert TypeInference.infer_from_name("func") == "Callable"

    def test_callback_suffix(self):
        """Should infer Callable from names ending with '_callback'."""
        assert TypeInference.infer_from_name("success_callback") == "Callable"

    def test_handler_suffix(self):
        """Should infer Callable from names ending with '_handler'."""
        assert TypeInference.infer_from_name("error_handler") == "Callable"

    # Case insensitivity
    def test_case_insensitive(self):
        """Should handle different cases."""
        assert TypeInference.infer_from_name("COUNT") == "int"
        assert TypeInference.infer_from_name("Count") == "int"
        assert TypeInference.infer_from_name("IS_ACTIVE") == "bool"

    # Unknown names
    def test_unknown(self):
        """Should return None for unknown patterns."""
        assert TypeInference.infer_from_name("xyz") is None
        assert TypeInference.infer_from_name("foo") is None


# =============================================================================
# TypeInference.infer_type Tests
# =============================================================================

class TestInferType:
    """Tests for TypeInference.infer_type."""

    def test_default_value_takes_precedence(self):
        """Default value should take precedence over name."""
        # 'count' would suggest int, but default value is a string
        expr = parse_expr('"hello"')
        result = TypeInference.infer_type(name="count", default_value=expr)
        assert result == "str"

    def test_falls_back_to_name(self):
        """Should fall back to name when default doesn't provide type."""
        # Unknown variable reference, but name suggests int
        expr = parse_expr("unknown_var")
        result = TypeInference.infer_type(name="count", default_value=expr)
        assert result == "int"

    def test_name_only(self):
        """Should infer from name when no default provided."""
        result = TypeInference.infer_type(name="count")
        assert result == "int"

    def test_default_only(self):
        """Should infer from default when no name provided."""
        expr = parse_expr("42")
        result = TypeInference.infer_type(default_value=expr)
        assert result == "int"

    def test_no_inference_possible(self):
        """Should return None when nothing can be inferred."""
        expr = parse_expr("unknown_var")
        result = TypeInference.infer_type(name="xyz", default_value=expr)
        assert result is None

    def test_none_arguments(self):
        """Should return None when both arguments are None."""
        result = TypeInference.infer_type()
        assert result is None
