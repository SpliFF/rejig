"""Tests for rope-backed cross-file rename operations.

Covers:
- ``Rejig.rename_function`` / ``Rejig.rename_class`` — definition + all
  callers/references rewritten by rope.
- ``FunctionTarget.rename`` / ``ClassTarget.rename`` delegate to rope by
  default; ``update_callers=False`` / ``update_references=False`` fall back
  to the single-file path.
- ``_resolve_source_file`` accepts ``str``, ``Path``, project-relative paths,
  and any ``Target`` exposing a ``file_path``.
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Generator

import pytest

from rejig import Rejig


@pytest.fixture
def multifile_project(tmp_path: Path) -> Path:
    """A two-file project where ``b.py`` calls / inherits from ``a.py``."""
    (tmp_path / "a.py").write_text(textwrap.dedent('''\
        def old_func(x):
            return x + 1


        class OldClass:
            def hello(self):
                return "hi"
    '''))
    (tmp_path / "b.py").write_text(textwrap.dedent('''\
        from a import old_func, OldClass


        def consumer():
            return old_func(41)


        class Sub(OldClass):
            pass
    '''))
    return tmp_path


@pytest.fixture
def rj(multifile_project: Path) -> Generator[Rejig, None, None]:
    with Rejig(str(multifile_project)) as instance:
        yield instance


class TestRenameFunctionCrossFile:
    """Rope rewrites the def AND every caller across the project."""

    def test_renames_definition_and_caller(self, rj: Rejig, multifile_project: Path) -> None:
        result = rj.rename_function("a.py", "old_func", "new_func")

        assert result.success is True
        a = (multifile_project / "a.py").read_text()
        b = (multifile_project / "b.py").read_text()
        assert "def new_func" in a and "old_func" not in a
        assert "new_func(41)" in b
        assert "from a import new_func, OldClass" in b
        assert "old_func" not in b

    def test_files_changed_lists_both_files(self, rj: Rejig, multifile_project: Path) -> None:
        result = rj.rename_function("a.py", "old_func", "new_func")
        paths = {p.name for p in result.files_changed}
        assert {"a.py", "b.py"} <= paths

    def test_missing_function_returns_failure(self, rj: Rejig) -> None:
        result = rj.rename_function("a.py", "no_such_func", "whatever")
        assert result.success is False
        assert "no_such_func" in result.message

    def test_dry_run_reports_without_writing(self, multifile_project: Path) -> None:
        original_a = (multifile_project / "a.py").read_text()
        original_b = (multifile_project / "b.py").read_text()
        with Rejig(str(multifile_project), dry_run=True) as rj:
            result = rj.rename_function("a.py", "old_func", "new_func")
        assert result.success is True
        assert "[DRY RUN]" in result.message
        assert (multifile_project / "a.py").read_text() == original_a
        assert (multifile_project / "b.py").read_text() == original_b


class TestRenameClassCrossFile:
    """Rope rewrites the class def AND every reference."""

    def test_renames_definition_and_subclass(self, rj: Rejig, multifile_project: Path) -> None:
        result = rj.rename_class("a.py", "OldClass", "NewClass")

        assert result.success is True
        a = (multifile_project / "a.py").read_text()
        b = (multifile_project / "b.py").read_text()
        assert "class NewClass" in a
        assert "OldClass" not in a
        assert "class Sub(NewClass)" in b
        assert "from a import old_func, NewClass" in b

    def test_missing_class_returns_failure(self, rj: Rejig) -> None:
        result = rj.rename_class("a.py", "NoSuchClass", "Whatever")
        assert result.success is False
        assert "NoSuchClass" in result.message


class TestFluentRenameDefaultsToRope:
    """FunctionTarget.rename / ClassTarget.rename delegate to rope by default."""

    def test_function_target_rename_updates_callers(
        self, rj: Rejig, multifile_project: Path
    ) -> None:
        result = rj.file("a.py").find_function("old_func").rename("new_func")
        assert result.success is True
        assert "new_func(41)" in (multifile_project / "b.py").read_text()

    def test_function_target_rename_update_callers_false_only_touches_def(
        self, rj: Rejig, multifile_project: Path
    ) -> None:
        result = rj.file("a.py").find_function("old_func").rename(
            "new_func", update_callers=False
        )
        assert result.success is True
        a = (multifile_project / "a.py").read_text()
        b = (multifile_project / "b.py").read_text()
        assert "def new_func" in a
        # caller untouched in this mode
        assert "old_func(41)" in b
        assert "from a import old_func" in b

    def test_class_target_rename_updates_references(
        self, rj: Rejig, multifile_project: Path
    ) -> None:
        result = rj.file("a.py").find_class("OldClass").rename("NewClass")
        assert result.success is True
        assert "class Sub(NewClass)" in (multifile_project / "b.py").read_text()


class TestSourceFileResolution:
    """rope APIs accept str, Path, project-relative paths, and Targets."""

    def test_accepts_absolute_path(self, rj: Rejig, multifile_project: Path) -> None:
        result = rj.rename_function(multifile_project / "a.py", "old_func", "new_func")
        assert result.success is True

    def test_accepts_relative_string(self, rj: Rejig, multifile_project: Path) -> None:
        result = rj.rename_function("a.py", "old_func", "new_func")
        assert result.success is True

    def test_accepts_function_target(self, rj: Rejig, multifile_project: Path) -> None:
        func = rj.file("a.py").find_function("old_func")
        result = rj.rename_function(func, "old_func", "new_func")
        assert result.success is True
        assert "def new_func" in (multifile_project / "a.py").read_text()

    def test_accepts_file_target(self, rj: Rejig, multifile_project: Path) -> None:
        file = rj.file("a.py")
        result = rj.rename_function(file, "old_func", "new_func")
        assert result.success is True
