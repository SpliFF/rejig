"""Tests for DependenciesTarget name/version parsing.

Regression coverage for the Poetry caret (``^``) / tilde (``~``) shorthand:
previously ``has()`` and ``get_version()`` only split on ``<>=!``, so
``josepy = "^1.0.0"`` parsed as the package name ``"josepy^1.0.0"`` and
never matched. Also covers extras stripping and PEP 508 specs.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig.project import PythonProject
from rejig.project.targets.dependencies import DependenciesTarget


POETRY_PYPROJECT = textwrap.dedent('''\
    [tool.poetry]
    name = "demo"
    version = "0.1.0"
    description = ""

    [tool.poetry.dependencies]
    python = "^3.10"
    josepy = "^1.0.0"
    requests = "~2.28"
    django = ">=4.2,<5.0"
    pydantic = { version = "^2.0", extras = ["email"] }
''')


PEP621_PYPROJECT = textwrap.dedent('''\
    [project]
    name = "demo"
    version = "0.1.0"
    dependencies = [
        "requests>=2.28.0",
        "django[bcrypt]>=4.2",
        "Some_Pkg==1.0",
    ]
''')


@pytest.fixture
def poetry_project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(POETRY_PYPROJECT)
    return tmp_path


@pytest.fixture
def pep621_project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(PEP621_PYPROJECT)
    return tmp_path


class TestSplitNameVersion:
    """The internal splitter handles every operator we care about."""

    @pytest.mark.parametrize(
        "spec, expected",
        [
            ("josepy^1.0.0", ("josepy", "^1.0.0")),
            ("requests~2.28", ("requests", "~2.28")),
            ("django>=4.2,<5.0", ("django", ">=4.2,<5.0")),
            ("Some_Pkg==1.0", ("Some_Pkg", "==1.0")),
            ("requests!=2.0", ("requests", "!=2.0")),
            ("django[bcrypt]>=4.2", ("django", ">=4.2")),
            ("pydantic[email]^2.0", ("pydantic", "^2.0")),
            ("nothing", ("nothing", None)),
            ("foo[extras]", ("foo", None)),
        ],
    )
    def test_split(self, spec: str, expected: tuple[str, str | None]) -> None:
        assert DependenciesTarget._split_name_version(spec) == expected


class TestPoetryDependencyLookups:
    def test_has_finds_caret_dependency(self, poetry_project: Path) -> None:
        deps = PythonProject(str(poetry_project)).dependencies()
        assert deps.has("josepy") is True

    def test_has_finds_tilde_dependency(self, poetry_project: Path) -> None:
        deps = PythonProject(str(poetry_project)).dependencies()
        assert deps.has("requests") is True

    def test_has_finds_pep508_style(self, poetry_project: Path) -> None:
        deps = PythonProject(str(poetry_project)).dependencies()
        assert deps.has("django") is True

    def test_has_finds_table_style(self, poetry_project: Path) -> None:
        deps = PythonProject(str(poetry_project)).dependencies()
        assert deps.has("pydantic") is True

    def test_has_misses_unknown(self, poetry_project: Path) -> None:
        deps = PythonProject(str(poetry_project)).dependencies()
        assert deps.has("not-installed") is False

    def test_get_version_caret(self, poetry_project: Path) -> None:
        deps = PythonProject(str(poetry_project)).dependencies()
        assert deps.get_version("josepy") == "^1.0.0"

    def test_get_version_tilde(self, poetry_project: Path) -> None:
        deps = PythonProject(str(poetry_project)).dependencies()
        assert deps.get_version("requests") == "~2.28"

    def test_get_version_pep508(self, poetry_project: Path) -> None:
        deps = PythonProject(str(poetry_project)).dependencies()
        assert deps.get_version("django") == ">=4.2,<5.0"

    def test_get_version_missing_returns_none(self, poetry_project: Path) -> None:
        deps = PythonProject(str(poetry_project)).dependencies()
        assert deps.get_version("nope") is None

    def test_update_replaces_version(self, poetry_project: Path) -> None:
        deps = PythonProject(str(poetry_project)).dependencies()
        result = deps.update("josepy", "^2.0.0")
        assert result.success is True
        assert deps.get_version("josepy") == "^2.0.0"


class TestPep621DependencyLookups:
    def test_has_with_extras(self, pep621_project: Path) -> None:
        deps = PythonProject(str(pep621_project)).dependencies()
        assert deps.has("django") is True

    def test_get_version_normalizes_name(self, pep621_project: Path) -> None:
        deps = PythonProject(str(pep621_project)).dependencies()
        # PEP 503 normalization: Some_Pkg -> some-pkg
        assert deps.has("some-pkg") is True
        assert deps.get_version("some-pkg") == "==1.0"
