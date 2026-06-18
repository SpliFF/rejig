"""Tests for FunctionTarget.replace_body and FunctionTarget.set_signature.

Covers:
- Body replacement preserves the existing docstring unless the new body
  starts with one.
- Body replacement rejects invalid syntax with an error Result, not an
  exception.
- ``set_signature`` can change params, return type, both, or neither.
- ``set_signature(return_type="")`` drops an existing annotation.
- Invalid param / return-type strings produce error Results.
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Generator

import pytest

from rejig import Rejig


SOURCE = textwrap.dedent('''\
    def has_docstring(x: int) -> int:
        """Return x doubled."""
        return x * 2


    def no_docstring(x: int) -> int:
        return x + 1


    def no_annotation(x):
        return x


    def with_default(name: str, count: int = 1) -> str:
        return name * count
''')


@pytest.fixture
def python_file(tmp_path: Path) -> Path:
    path = tmp_path / "lib.py"
    path.write_text(SOURCE)
    return path


@pytest.fixture
def rj(tmp_path: Path, python_file: Path) -> Generator[Rejig, None, None]:
    with Rejig(str(tmp_path)) as instance:
        yield instance


class TestReplaceBody:
    def test_replaces_single_statement_body(
        self, rj: Rejig, python_file: Path
    ) -> None:
        result = rj.file(python_file.name).find_function("no_docstring").replace_body(
            "return x * 100"
        )
        assert result.success is True
        content = python_file.read_text()
        assert "return x * 100" in content
        assert "return x + 1" not in content

    def test_replaces_multi_statement_body(self, rj: Rejig, python_file: Path) -> None:
        new_body = textwrap.dedent('''\
            if x < 0:
                return 0
            return x * 3
        ''')
        result = rj.file(python_file.name).find_function("no_docstring").replace_body(new_body)
        assert result.success is True
        content = python_file.read_text()
        assert "if x < 0:" in content
        assert "return x * 3" in content

    def test_preserves_docstring_when_new_body_lacks_one(
        self, rj: Rejig, python_file: Path
    ) -> None:
        result = rj.file(python_file.name).find_function("has_docstring").replace_body(
            "return x * 10"
        )
        assert result.success is True
        content = python_file.read_text()
        assert '"""Return x doubled."""' in content
        assert "return x * 10" in content
        assert "return x * 2" not in content

    def test_new_docstring_replaces_old(self, rj: Rejig, python_file: Path) -> None:
        new_body = textwrap.dedent('''\
            """A new description."""
            return x * 10
        ''')
        result = rj.file(python_file.name).find_function("has_docstring").replace_body(new_body)
        assert result.success is True
        content = python_file.read_text()
        assert '"""A new description."""' in content
        assert '"""Return x doubled."""' not in content

    def test_invalid_syntax_returns_error_result(
        self, rj: Rejig, python_file: Path
    ) -> None:
        result = rj.file(python_file.name).find_function("no_docstring").replace_body(
            "def malformed("
        )
        assert result.success is False
        assert "Invalid body syntax" in result.message

    def test_missing_function_fails_gracefully(
        self, rj: Rejig, python_file: Path
    ) -> None:
        result = rj.file(python_file.name).find_function("ghost").replace_body("return 0")
        assert result.success is False


class TestSetSignature:
    def test_set_params_only(self, rj: Rejig, python_file: Path) -> None:
        result = rj.file(python_file.name).find_function("no_docstring").set_signature(
            params="x: int, y: int = 0"
        )
        assert result.success is True
        content = python_file.read_text()
        assert "def no_docstring(x: int, y: int = 0) -> int:" in content

    def test_set_return_type_only(self, rj: Rejig, python_file: Path) -> None:
        result = rj.file(python_file.name).find_function("no_annotation").set_signature(
            return_type="int"
        )
        assert result.success is True
        assert "def no_annotation(x) -> int:" in python_file.read_text()

    def test_set_both_params_and_return(self, rj: Rejig, python_file: Path) -> None:
        result = rj.file(python_file.name).find_function("no_annotation").set_signature(
            params="x: float, y: float", return_type="float"
        )
        assert result.success is True
        assert "def no_annotation(x: float, y: float) -> float:" in python_file.read_text()

    def test_empty_return_type_drops_annotation(
        self, rj: Rejig, python_file: Path
    ) -> None:
        result = rj.file(python_file.name).find_function("no_docstring").set_signature(
            return_type=""
        )
        assert result.success is True
        content = python_file.read_text()
        assert "def no_docstring(x: int):" in content
        assert "def no_docstring(x: int) ->" not in content

    def test_empty_params_clears_parameters(
        self, rj: Rejig, python_file: Path
    ) -> None:
        result = rj.file(python_file.name).find_function("with_default").set_signature(
            params=""
        )
        assert result.success is True
        assert "def with_default() -> str:" in python_file.read_text()

    def test_no_changes_requested_succeeds_noop(
        self, rj: Rejig, python_file: Path
    ) -> None:
        before = python_file.read_text()
        result = rj.file(python_file.name).find_function("no_docstring").set_signature()
        assert result.success is True
        assert python_file.read_text() == before

    def test_invalid_params_returns_error(self, rj: Rejig, python_file: Path) -> None:
        result = rj.file(python_file.name).find_function("no_docstring").set_signature(
            params="x: int,,"
        )
        assert result.success is False
        assert "Invalid params" in result.message

    def test_invalid_return_type_returns_error(
        self, rj: Rejig, python_file: Path
    ) -> None:
        result = rj.file(python_file.name).find_function("no_docstring").set_signature(
            return_type="def"
        )
        assert result.success is False
        assert "Invalid return type" in result.message

    def test_missing_function_fails(self, rj: Rejig, python_file: Path) -> None:
        result = rj.file(python_file.name).find_function("ghost").set_signature(
            return_type="int"
        )
        assert result.success is False
