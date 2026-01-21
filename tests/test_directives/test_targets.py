"""
Tests for rejig.directives.targets module.

This module tests DirectiveTarget and DirectiveTargetList:
- DirectiveTarget for individual directive operations
- DirectiveTargetList for batch operations on directives

DirectiveTarget represents a linting directive comment in a file,
providing operations like delete, add_code, remove_code, and set_reason.

Coverage targets:
- DirectiveTarget properties (file_path, line_number, codes, etc.)
- exists() for directive existence checks
- get_content() for line retrieval
- delete()/remove() for directive removal
- add_code() for adding error codes
- remove_code() for removing error codes
- set_reason() for adding/updating reason comments
- Dry run mode for all operations
- DirectiveTargetList filtering methods
- DirectiveTargetList batch operations
- DirectiveTargetList statistics methods
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rejig import Rejig
from rejig.directives.parser import ParsedDirective
from rejig.directives.targets import DirectiveTarget, DirectiveTargetList


# =============================================================================
# DirectiveTarget Basic Tests
# =============================================================================

class TestDirectiveTargetBasic:
    """Tests for basic DirectiveTarget operations."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a sample Python file with directives."""
        content = '''\
x = foo()  # type: ignore[arg-type]
y = bar()  # noqa: E501
z = baz()  # pragma: no cover
'''
        file_path = tmp_path / "sample.py"
        file_path.write_text(content)
        return file_path

    def test_directive_target_properties(self, rejig: Rejig, python_file: Path):
        """
        DirectiveTarget should expose directive properties.

        A DirectiveTarget wraps a ParsedDirective with file location info.
        It exposes properties like directive_type, codes, line_number, etc.
        """
        directive = ParsedDirective(
            directive_type="type_ignore",
            codes=["arg-type"],
            reason="Legacy code",
            raw_text="# type: ignore[arg-type]  # Legacy code",
        )
        target = DirectiveTarget(rejig, python_file, 1, directive)

        # Check basic properties
        assert target.file_path == python_file
        assert target.path == python_file
        assert target.line_number == 1
        assert target.directive_type == "type_ignore"
        assert target.codes == ["arg-type"]
        assert target.reason == "Legacy code"
        assert target.raw_text == "# type: ignore[arg-type]  # Legacy code"

    def test_is_bare_property(self, rejig: Rejig, python_file: Path):
        """
        is_bare should return True for directives without codes.

        Bare directives like "# type: ignore" suppress all errors of that type.
        """
        bare_directive = ParsedDirective(
            directive_type="type_ignore",
            codes=[],
        )
        target = DirectiveTarget(rejig, python_file, 1, bare_directive)

        assert target.is_bare is True
        assert target.is_specific is False

    def test_is_specific_property(self, rejig: Rejig, python_file: Path):
        """
        is_specific should return True for directives with codes.

        Specific directives like "# type: ignore[arg-type]" target specific errors.
        """
        specific_directive = ParsedDirective(
            directive_type="type_ignore",
            codes=["arg-type"],
        )
        target = DirectiveTarget(rejig, python_file, 1, specific_directive)

        assert target.is_specific is True
        assert target.is_bare is False

    def test_location_property(self, rejig: Rejig, python_file: Path):
        """
        location should return "file:line" string.

        This is useful for logging and error messages.
        """
        directive = ParsedDirective(directive_type="type_ignore", codes=[])
        target = DirectiveTarget(rejig, python_file, 5, directive)

        assert target.location == f"{python_file}:5"

    def test_repr(self, rejig: Rejig, python_file: Path):
        """
        DirectiveTarget should have a useful string representation.
        """
        directive = ParsedDirective(
            directive_type="type_ignore",
            codes=["arg-type"],
        )
        target = DirectiveTarget(rejig, python_file, 3, directive)

        repr_str = repr(target)
        assert "DirectiveTarget" in repr_str
        assert "type_ignore" in repr_str
        assert "arg-type" in repr_str


# =============================================================================
# DirectiveTarget exists() Tests
# =============================================================================

class TestDirectiveTargetExists:
    """Tests for DirectiveTarget.exists() method."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_exists_returns_true(self, rejig: Rejig, tmp_path: Path):
        """
        exists() should return True when directive is present in file.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = 1  # type: ignore\n")

        directive = ParsedDirective(directive_type="type_ignore", codes=[])
        target = DirectiveTarget(rejig, file_path, 1, directive)

        assert target.exists() is True

    def test_exists_returns_false_file_missing(self, rejig: Rejig, tmp_path: Path):
        """
        exists() should return False when file doesn't exist.
        """
        directive = ParsedDirective(directive_type="type_ignore", codes=[])
        target = DirectiveTarget(rejig, tmp_path / "missing.py", 1, directive)

        assert target.exists() is False

    def test_exists_returns_false_line_out_of_range(self, rejig: Rejig, tmp_path: Path):
        """
        exists() should return False when line number exceeds file length.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = 1\n")

        directive = ParsedDirective(directive_type="type_ignore", codes=[])
        target = DirectiveTarget(rejig, file_path, 100, directive)

        assert target.exists() is False

    def test_exists_returns_false_directive_removed(self, rejig: Rejig, tmp_path: Path):
        """
        exists() should return False when directive was removed from line.

        This simulates the case where the file was modified externally.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = 1  # just a comment\n")

        directive = ParsedDirective(directive_type="type_ignore", codes=[])
        target = DirectiveTarget(rejig, file_path, 1, directive)

        # The target was created when type: ignore existed, but now it's gone
        assert target.exists() is False


# =============================================================================
# DirectiveTarget get_content() Tests
# =============================================================================

class TestDirectiveTargetGetContent:
    """Tests for DirectiveTarget.get_content() method."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_get_content_success(self, rejig: Rejig, tmp_path: Path):
        """
        get_content() should return the line containing the directive.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = foo()  # type: ignore[arg-type]\n")

        directive = ParsedDirective(directive_type="type_ignore", codes=["arg-type"])
        target = DirectiveTarget(rejig, file_path, 1, directive)

        result = target.get_content()

        assert result.success is True
        assert "x = foo()" in result.data
        assert "# type: ignore[arg-type]" in result.data

    def test_get_content_file_not_found(self, rejig: Rejig, tmp_path: Path):
        """
        get_content() should fail for missing files.
        """
        directive = ParsedDirective(directive_type="type_ignore", codes=[])
        target = DirectiveTarget(rejig, tmp_path / "missing.py", 1, directive)

        result = target.get_content()

        assert result.success is False
        assert "not found" in result.message.lower()

    def test_get_content_line_out_of_range(self, rejig: Rejig, tmp_path: Path):
        """
        get_content() should fail for out-of-range line numbers.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = 1\n")

        directive = ParsedDirective(directive_type="type_ignore", codes=[])
        target = DirectiveTarget(rejig, file_path, 100, directive)

        result = target.get_content()

        assert result.success is False
        assert "out of range" in result.message.lower()


# =============================================================================
# DirectiveTarget delete() Tests
# =============================================================================

class TestDirectiveTargetDelete:
    """Tests for DirectiveTarget.delete() method."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_delete_type_ignore(self, rejig: Rejig, tmp_path: Path):
        """
        delete() should remove a type: ignore directive from the line.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = foo()  # type: ignore[arg-type]\n")

        directive = ParsedDirective(directive_type="type_ignore", codes=["arg-type"])
        target = DirectiveTarget(rejig, file_path, 1, directive)

        result = target.delete()

        assert result.success is True
        content = file_path.read_text()
        assert "# type: ignore" not in content

    def test_delete_noqa(self, rejig: Rejig, tmp_path: Path):
        """
        delete() should remove a noqa directive from the line.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("long_line = 123  # noqa: E501\n")

        directive = ParsedDirective(directive_type="noqa", codes=["E501"])
        target = DirectiveTarget(rejig, file_path, 1, directive)

        result = target.delete()

        assert result.success is True
        content = file_path.read_text()
        assert "# noqa" not in content

    def test_remove_is_alias(self, rejig: Rejig, tmp_path: Path):
        """
        remove() should be an alias for delete().
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = 1  # type: ignore\n")

        directive = ParsedDirective(directive_type="type_ignore", codes=[])
        target = DirectiveTarget(rejig, file_path, 1, directive)

        result = target.remove()

        assert result.success is True
        content = file_path.read_text()
        assert "# type: ignore" not in content

    def test_delete_file_not_found(self, rejig: Rejig, tmp_path: Path):
        """
        delete() should fail for missing files.
        """
        directive = ParsedDirective(directive_type="type_ignore", codes=[])
        target = DirectiveTarget(rejig, tmp_path / "missing.py", 1, directive)

        result = target.delete()

        assert result.success is False
        assert "not found" in result.message.lower()

    def test_delete_dry_run(self, tmp_path: Path):
        """
        In dry run mode, delete() should not modify the file.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = 1  # type: ignore\n")

        rejig = Rejig(str(tmp_path), dry_run=True)
        directive = ParsedDirective(directive_type="type_ignore", codes=[])
        target = DirectiveTarget(rejig, file_path, 1, directive)

        result = target.delete()

        assert result.success is True
        assert "DRY RUN" in result.message
        # File should be unchanged
        content = file_path.read_text()
        assert "# type: ignore" in content


# =============================================================================
# DirectiveTarget add_code() Tests
# =============================================================================

class TestDirectiveTargetAddCode:
    """Tests for DirectiveTarget.add_code() method."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_add_code_to_type_ignore(self, rejig: Rejig, tmp_path: Path):
        """
        add_code() should add an error code to a type: ignore directive.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = foo()  # type: ignore[arg-type]\n")

        directive = ParsedDirective(directive_type="type_ignore", codes=["arg-type"])
        target = DirectiveTarget(rejig, file_path, 1, directive)

        result = target.add_code("return-value")

        assert result.success is True
        content = file_path.read_text()
        assert "return-value" in content

    def test_add_code_to_noqa(self, rejig: Rejig, tmp_path: Path):
        """
        add_code() should add an error code to a noqa directive.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = 1  # noqa: E501\n")

        directive = ParsedDirective(directive_type="noqa", codes=["E501"])
        target = DirectiveTarget(rejig, file_path, 1, directive)

        result = target.add_code("F401")

        assert result.success is True
        content = file_path.read_text()
        assert "F401" in content

    def test_add_code_already_present(self, rejig: Rejig, tmp_path: Path):
        """
        add_code() should succeed without duplicating existing codes.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = 1  # type: ignore[arg-type]\n")

        directive = ParsedDirective(directive_type="type_ignore", codes=["arg-type"])
        target = DirectiveTarget(rejig, file_path, 1, directive)

        result = target.add_code("arg-type")

        assert result.success is True
        assert "already" in result.message

    def test_add_code_dry_run(self, tmp_path: Path):
        """
        In dry run mode, add_code() should not modify the file.
        """
        file_path = tmp_path / "test.py"
        original = "x = 1  # type: ignore[arg-type]\n"
        file_path.write_text(original)

        rejig = Rejig(str(tmp_path), dry_run=True)
        directive = ParsedDirective(directive_type="type_ignore", codes=["arg-type"])
        target = DirectiveTarget(rejig, file_path, 1, directive)

        result = target.add_code("return-value")

        assert result.success is True
        assert "DRY RUN" in result.message
        # File should be unchanged
        content = file_path.read_text()
        assert content == original


# =============================================================================
# DirectiveTarget remove_code() Tests
# =============================================================================

class TestDirectiveTargetRemoveCode:
    """Tests for DirectiveTarget.remove_code() method."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_remove_code_from_type_ignore(self, rejig: Rejig, tmp_path: Path):
        """
        remove_code() should remove an error code from a type: ignore directive.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = foo()  # type: ignore[arg-type, return-value]\n")

        directive = ParsedDirective(
            directive_type="type_ignore",
            codes=["arg-type", "return-value"],
        )
        target = DirectiveTarget(rejig, file_path, 1, directive)

        result = target.remove_code("arg-type")

        assert result.success is True
        content = file_path.read_text()
        assert "arg-type" not in content
        assert "return-value" in content

    def test_remove_code_not_in_directive(self, rejig: Rejig, tmp_path: Path):
        """
        remove_code() should succeed when code isn't present (no-op).
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = 1  # type: ignore[arg-type]\n")

        directive = ParsedDirective(directive_type="type_ignore", codes=["arg-type"])
        target = DirectiveTarget(rejig, file_path, 1, directive)

        result = target.remove_code("other-code")

        assert result.success is True
        assert "not in" in result.message

    def test_remove_only_code_fails(self, rejig: Rejig, tmp_path: Path):
        """
        remove_code() should fail when trying to remove the only code.

        Use delete() instead to remove the entire directive.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = 1  # type: ignore[arg-type]\n")

        directive = ParsedDirective(directive_type="type_ignore", codes=["arg-type"])
        target = DirectiveTarget(rejig, file_path, 1, directive)

        result = target.remove_code("arg-type")

        assert result.success is False
        assert "only code" in result.message.lower()


# =============================================================================
# DirectiveTarget set_reason() Tests
# =============================================================================

class TestDirectiveTargetSetReason:
    """Tests for DirectiveTarget.set_reason() method."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_set_reason_on_type_ignore(self, rejig: Rejig, tmp_path: Path):
        """
        set_reason() should add a reason comment to a type: ignore directive.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = foo()  # type: ignore[arg-type]\n")

        directive = ParsedDirective(directive_type="type_ignore", codes=["arg-type"])
        target = DirectiveTarget(rejig, file_path, 1, directive)

        result = target.set_reason("Legacy API")

        assert result.success is True
        content = file_path.read_text()
        assert "Legacy API" in content

    def test_set_reason_on_noqa(self, rejig: Rejig, tmp_path: Path):
        """
        set_reason() should add a reason comment to a noqa directive.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = 1  # noqa: E501\n")

        directive = ParsedDirective(directive_type="noqa", codes=["E501"])
        target = DirectiveTarget(rejig, file_path, 1, directive)

        result = target.set_reason("Long string literal")

        assert result.success is True
        content = file_path.read_text()
        assert "Long string literal" in content

    def test_set_reason_dry_run(self, tmp_path: Path):
        """
        In dry run mode, set_reason() should not modify the file.
        """
        file_path = tmp_path / "test.py"
        original = "x = 1  # type: ignore\n"
        file_path.write_text(original)

        rejig = Rejig(str(tmp_path), dry_run=True)
        directive = ParsedDirective(directive_type="type_ignore", codes=[])
        target = DirectiveTarget(rejig, file_path, 1, directive)

        result = target.set_reason("Some reason")

        assert result.success is True
        assert "DRY RUN" in result.message
        # File should be unchanged
        content = file_path.read_text()
        assert "Some reason" not in content


# =============================================================================
# DirectiveTargetList Filtering Tests
# =============================================================================

class TestDirectiveTargetListFiltering:
    """Tests for DirectiveTargetList filtering methods."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a file with various directives for testing."""
        content = '''\
x = 1  # type: ignore
y = 2  # type: ignore[arg-type]
z = 3  # noqa
w = 4  # noqa: E501
'''
        file_path = tmp_path / "test.py"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def directive_list(self, rejig: Rejig, python_file: Path) -> DirectiveTargetList:
        """Create a DirectiveTargetList with mixed directives."""
        targets = [
            DirectiveTarget(
                rejig, python_file, 1,
                ParsedDirective(directive_type="type_ignore", codes=[]),
            ),
            DirectiveTarget(
                rejig, python_file, 2,
                ParsedDirective(directive_type="type_ignore", codes=["arg-type"]),
            ),
            DirectiveTarget(
                rejig, python_file, 3,
                ParsedDirective(directive_type="noqa", codes=[]),
            ),
            DirectiveTarget(
                rejig, python_file, 4,
                ParsedDirective(directive_type="noqa", codes=["E501"]),
            ),
        ]
        return DirectiveTargetList(rejig, targets)

    def test_by_type(self, directive_list: DirectiveTargetList):
        """
        by_type() should filter to directives of a specific type.
        """
        type_ignores = directive_list.by_type("type_ignore")

        assert len(type_ignores) == 2
        for d in type_ignores:
            assert d.directive_type == "type_ignore"

    def test_bare(self, directive_list: DirectiveTargetList):
        """
        bare() should filter to directives without specific codes.
        """
        bare = directive_list.bare()

        assert len(bare) == 2
        for d in bare:
            assert d.is_bare is True

    def test_specific(self, directive_list: DirectiveTargetList):
        """
        specific() should filter to directives with specific codes.
        """
        specific = directive_list.specific()

        assert len(specific) == 2
        for d in specific:
            assert d.is_specific is True

    def test_with_code(self, directive_list: DirectiveTargetList):
        """
        with_code() should filter to directives containing a specific code.
        """
        with_arg_type = directive_list.with_code("arg-type")

        assert len(with_arg_type) == 1
        assert "arg-type" in with_arg_type[0].codes

    def test_without_reason(self, rejig: Rejig, tmp_path: Path):
        """
        without_reason() should filter to directives without reason comments.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = 1\ny = 2\n")

        targets = [
            DirectiveTarget(
                rejig, file_path, 1,
                ParsedDirective(directive_type="type_ignore", codes=[], reason=None),
            ),
            DirectiveTarget(
                rejig, file_path, 2,
                ParsedDirective(directive_type="type_ignore", codes=[], reason="Has reason"),
            ),
        ]
        directive_list = DirectiveTargetList(rejig, targets)

        no_reason = directive_list.without_reason()

        assert len(no_reason) == 1
        assert no_reason[0].reason is None

    def test_with_reason(self, rejig: Rejig, tmp_path: Path):
        """
        with_reason() should filter to directives with reason comments.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = 1\ny = 2\n")

        targets = [
            DirectiveTarget(
                rejig, file_path, 1,
                ParsedDirective(directive_type="type_ignore", codes=[], reason=None),
            ),
            DirectiveTarget(
                rejig, file_path, 2,
                ParsedDirective(directive_type="type_ignore", codes=[], reason="Has reason"),
            ),
        ]
        directive_list = DirectiveTargetList(rejig, targets)

        has_reason = directive_list.with_reason()

        assert len(has_reason) == 1
        assert has_reason[0].reason == "Has reason"

    def test_in_file(self, rejig: Rejig, tmp_path: Path):
        """
        in_file() should filter to directives in a specific file.
        """
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("x = 1\n")
        file2.write_text("y = 2\n")

        targets = [
            DirectiveTarget(
                rejig, file1, 1,
                ParsedDirective(directive_type="type_ignore", codes=[]),
            ),
            DirectiveTarget(
                rejig, file2, 1,
                ParsedDirective(directive_type="noqa", codes=[]),
            ),
        ]
        directive_list = DirectiveTargetList(rejig, targets)

        in_file1 = directive_list.in_file(file1)

        assert len(in_file1) == 1
        assert in_file1[0].file_path == file1

    def test_filter_with_predicate(self, directive_list: DirectiveTargetList):
        """
        filter() should apply a custom predicate function.
        """
        # Filter to directives on even line numbers
        even_lines = directive_list.filter(lambda d: d.line_number % 2 == 0)

        assert len(even_lines) == 2
        for d in even_lines:
            assert d.line_number % 2 == 0


# =============================================================================
# DirectiveTargetList Statistics Tests
# =============================================================================

class TestDirectiveTargetListStatistics:
    """Tests for DirectiveTargetList statistics methods."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    @pytest.fixture
    def directive_list(self, rejig: Rejig, tmp_path: Path) -> DirectiveTargetList:
        """Create a DirectiveTargetList for statistics testing."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("x = 1\ny = 2\n")
        file2.write_text("z = 3\n")

        targets = [
            DirectiveTarget(
                rejig, file1, 1,
                ParsedDirective(directive_type="type_ignore", codes=["arg-type"]),
            ),
            DirectiveTarget(
                rejig, file1, 2,
                ParsedDirective(directive_type="type_ignore", codes=["return-value"]),
            ),
            DirectiveTarget(
                rejig, file2, 1,
                ParsedDirective(directive_type="noqa", codes=["E501", "arg-type"]),
            ),
        ]
        return DirectiveTargetList(rejig, targets)

    def test_count_by_type(self, directive_list: DirectiveTargetList):
        """
        count_by_type() should return counts of directives per type.
        """
        counts = directive_list.count_by_type()

        assert counts["type_ignore"] == 2
        assert counts["noqa"] == 1

    def test_count_by_file(self, directive_list: DirectiveTargetList, tmp_path: Path):
        """
        count_by_file() should return counts of directives per file.
        """
        counts = directive_list.count_by_file()

        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        assert counts[file1] == 2
        assert counts[file2] == 1

    def test_count_by_code(self, directive_list: DirectiveTargetList):
        """
        count_by_code() should return counts of directives per error code.
        """
        counts = directive_list.count_by_code()

        # arg-type appears in two directives
        assert counts["arg-type"] == 2
        assert counts["return-value"] == 1
        assert counts["E501"] == 1


# =============================================================================
# DirectiveTargetList Batch Operations Tests
# =============================================================================

class TestDirectiveTargetListBatchOps:
    """Tests for DirectiveTargetList batch operations."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_remove_all(self, rejig: Rejig, tmp_path: Path):
        """
        remove_all() should remove all directives in the list.

        BatchResult.succeeded property contains the list of successful results.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text('''\
x = 1  # type: ignore
y = 2  # noqa
''')

        targets = [
            DirectiveTarget(
                rejig, file_path, 1,
                ParsedDirective(directive_type="type_ignore", codes=[]),
            ),
            DirectiveTarget(
                rejig, file_path, 2,
                ParsedDirective(directive_type="noqa", codes=[]),
            ),
        ]
        directive_list = DirectiveTargetList(rejig, targets)

        result = directive_list.remove_all()

        # BatchResult uses succeeded (list) not success_count
        assert len(result.succeeded) == 2
        content = file_path.read_text()
        assert "# type: ignore" not in content
        assert "# noqa" not in content

    def test_delete_is_alias_for_remove_all(self, rejig: Rejig, tmp_path: Path):
        """
        delete() should be an alias for remove_all().
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = 1  # type: ignore\n")

        targets = [
            DirectiveTarget(
                rejig, file_path, 1,
                ParsedDirective(directive_type="type_ignore", codes=[]),
            ),
        ]
        directive_list = DirectiveTargetList(rejig, targets)

        result = directive_list.delete()

        assert len(result.succeeded) == 1

    def test_add_reason_all(self, rejig: Rejig, tmp_path: Path):
        """
        add_reason_all() should add a reason to all directives.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text('''\
x = 1  # type: ignore[arg-type]
y = 2  # noqa: E501
''')

        targets = [
            DirectiveTarget(
                rejig, file_path, 1,
                ParsedDirective(directive_type="type_ignore", codes=["arg-type"]),
            ),
            DirectiveTarget(
                rejig, file_path, 2,
                ParsedDirective(directive_type="noqa", codes=["E501"]),
            ),
        ]
        directive_list = DirectiveTargetList(rejig, targets)

        result = directive_list.add_reason_all("Legacy code")

        assert len(result.succeeded) == 2
        content = file_path.read_text()
        assert content.count("Legacy code") == 2

    def test_repr(self, rejig: Rejig, tmp_path: Path):
        """
        DirectiveTargetList should have a useful string representation.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("x = 1\n")

        targets = [
            DirectiveTarget(
                rejig, file_path, 1,
                ParsedDirective(directive_type="type_ignore", codes=[]),
            ),
        ]
        directive_list = DirectiveTargetList(rejig, targets)

        repr_str = repr(directive_list)
        assert "DirectiveTargetList" in repr_str
        assert "1" in repr_str
