"""Tests for DependenciesTarget.remove() comment and whitespace handling.

Regression coverage for two defects in the Poetry branch of ``remove()``:

- It did a plain ``del section[name]``, which removes only the key/value pair.
  Standalone comments are separate items in the tomlkit container, so the lines
  documenting an entry survived it and ended up orphaned above whatever followed.
- It looked the key up with the caller's raw spelling while ``has()`` compared
  normalised names, so ``remove("foo_bar")`` against a ``foo-bar`` key passed the
  guard, matched nothing, and still reported success.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig.project import PythonProject


POETRY_PYPROJECT = textwrap.dedent('''\
    [tool.poetry]
    name = "demo"
    version = "0.1.0"

    [tool.poetry.dependencies]
    python = "^3.10"
    requests = "^2.28"

    # better django authentication
    rules = "*"

    # PVE-2025-82038 (https://data.safetycli.com/v/82038/eda)
    sqlparse = "^0.5.4"

    # Okta authentication support
    mozilla-django-oidc = "*"
''')


@pytest.fixture
def poetry_project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(POETRY_PYPROJECT)
    return tmp_path


def content(root: Path) -> str:
    return (root / "pyproject.toml").read_text()


class TestRemoveTakesAttachedComment:
    def test_removes_the_comment_documenting_the_entry(self, poetry_project: Path) -> None:
        PythonProject(str(poetry_project)).dependencies().remove("sqlparse")

        result = content(poetry_project)
        assert "sqlparse" not in result
        assert "82038" not in result

    def test_leaves_one_blank_line_between_neighbouring_blocks(
        self, poetry_project: Path
    ) -> None:
        PythonProject(str(poetry_project)).dependencies().remove("sqlparse")

        assert 'rules = "*"\n\n# Okta' in content(poetry_project)

    def test_leaves_surrounding_entries_untouched(self, poetry_project: Path) -> None:
        PythonProject(str(poetry_project)).dependencies().remove("sqlparse")

        result = content(poetry_project)
        assert "# better django authentication\nrules" in result
        assert "# Okta authentication support\nmozilla-django-oidc" in result
        assert 'python = "^3.10"' in result

    def test_removes_a_multi_line_comment_block(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            textwrap.dedent('''\
                [tool.poetry.dependencies]
                a = "^1.0"

                # first line
                # second line
                b = "^2.0"

                c = "^3.0"
            ''')
        )

        PythonProject(str(tmp_path)).dependencies().remove("b")

        result = content(tmp_path)
        assert "first line" not in result
        assert "second line" not in result
        assert 'a = "^1.0"\n\nc = "^3.0"' in result

    def test_keeps_a_comment_separated_by_a_blank_line(self, tmp_path: Path) -> None:
        """A blank line means the comment introduces the section, not the entry."""
        (tmp_path / "pyproject.toml").write_text(
            textwrap.dedent('''\
                [tool.poetry.dependencies]
                # these are the runtime deps

                b = "^2.0"
                c = "^3.0"
            ''')
        )

        PythonProject(str(tmp_path)).dependencies().remove("b")

        result = content(tmp_path)
        assert "these are the runtime deps" in result
        assert "b =" not in result

    def test_no_comment_to_take(self, poetry_project: Path) -> None:
        PythonProject(str(poetry_project)).dependencies().remove("requests")

        result = content(poetry_project)
        assert "requests" not in result
        assert "# better django authentication\nrules" in result
        assert 'python = "^3.10"' in result

    def test_comments_false_keeps_the_comment(self, tmp_path: Path) -> None:
        from rejig._tomlkit_io import loads_toml, remove_key

        doc = loads_toml('[deps]\n# doc\nb = "2"\n')
        assert remove_key(doc["deps"], "b", comments=False) is True

        import tomlkit

        assert "# doc" in tomlkit.dumps(doc)


class TestRemoveNormalisesTheKey:
    @pytest.mark.parametrize("spelling", ["mozilla_django_oidc", "Mozilla-Django-OIDC"])
    def test_removes_despite_separator_or_case_differences(
        self, poetry_project: Path, spelling: str
    ) -> None:
        deps = PythonProject(str(poetry_project)).dependencies()
        assert deps.has(spelling) is True

        deps.remove(spelling)

        assert "mozilla-django-oidc" not in content(poetry_project)

    def test_absent_dependency_is_a_no_op(self, poetry_project: Path) -> None:
        before = content(poetry_project)
        result = PythonProject(str(poetry_project)).dependencies().remove("not-here")

        assert result.success is True
        assert content(poetry_project) == before
