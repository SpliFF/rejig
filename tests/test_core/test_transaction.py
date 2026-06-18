"""
Tests for rejig.core.transaction module.

This module tests the Transaction class for atomic batch operations:
- Adding changes to a transaction
- Commit with actual file writes
- Rollback discarding pending changes
- Dry-run mode within transactions
- Error handling: double commit, commit after rollback, nested changes
- Transaction state tracking (pending_count, pending_files, preview)

Coverage targets:
- PendingChange creation and chaining
- Transaction.add_change
- Transaction.commit (normal, dry-run, empty, failure rollback)
- Transaction.rollback
- Transaction.get_current_content
- Transaction properties: pending_count, pending_files, preview
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.core.results import BatchResult, ErrorResult, Result
from rejig.core.transaction import PendingChange, Transaction


# =============================================================================
# PendingChange Tests
# =============================================================================

class TestPendingChange:
    """Tests for PendingChange dataclass."""

    def test_pending_change_creation(self, tmp_path: Path):
        """
        PendingChange should store all relevant change data.
        """
        path = tmp_path / "test.py"
        change = PendingChange(
            path=path,
            original_content="old",
            new_content="new",
            operation="test operation",
        )

        assert change.path == path
        assert change.original_content == "old"
        assert change.new_content == "new"
        assert change.operation == "test operation"


# =============================================================================
# Transaction Basic Tests
# =============================================================================

class TestTransactionBasics:
    """Tests for basic Transaction functionality."""

    def test_transaction_initial_state(self, rejig: Rejig):
        """
        A new transaction should have no pending changes.
        """
        with rejig.transaction() as tx:
            assert tx.pending_count == 0
            assert tx.pending_files == []
            tx.rollback()

    def test_add_change_records_pending(self, rejig: Rejig, tmp_python_project: Path):
        """
        add_change should record a pending change without writing to disk.
        """
        file_path = tmp_python_project / "src" / "models.py"
        original = file_path.read_text()

        with rejig.transaction() as tx:
            result = tx.add_change(
                path=file_path,
                original=original,
                new_content=original + "\n# added\n",
                operation="add comment",
            )

            # Should return a pending result
            assert result.success is True
            assert "[PENDING]" in result.message

            # Transaction should track the change
            assert tx.pending_count == 1
            assert file_path in tx.pending_files

            # File should NOT be modified yet
            assert file_path.read_text() == original

            tx.rollback()

    def test_add_multiple_changes_same_file(self, rejig: Rejig, tmp_python_project: Path):
        """
        Multiple changes to the same file should chain correctly.
        The original content should be preserved from the first change.
        """
        file_path = tmp_python_project / "src" / "models.py"
        original = file_path.read_text()

        with rejig.transaction() as tx:
            # First change
            tx.add_change(
                path=file_path,
                original=original,
                new_content=original + "\n# first\n",
                operation="add first",
            )

            # Second change (builds on first)
            tx.add_change(
                path=file_path,
                original=original + "\n# first\n",
                new_content=original + "\n# first\n# second\n",
                operation="add second",
            )

            # Should still count as one pending file
            assert tx.pending_count == 1

            tx.rollback()

    def test_add_changes_different_files(self, rejig: Rejig, tmp_python_project: Path):
        """
        Changes to different files should be tracked independently.
        """
        models_path = tmp_python_project / "src" / "models.py"
        utils_path = tmp_python_project / "src" / "utils.py"
        models_original = models_path.read_text()
        utils_original = utils_path.read_text()

        with rejig.transaction() as tx:
            tx.add_change(
                path=models_path,
                original=models_original,
                new_content=models_original + "\n# change1\n",
                operation="modify models",
            )
            tx.add_change(
                path=utils_path,
                original=utils_original,
                new_content=utils_original + "\n# change2\n",
                operation="modify utils",
            )

            assert tx.pending_count == 2
            assert models_path in tx.pending_files
            assert utils_path in tx.pending_files

            tx.rollback()


# =============================================================================
# Transaction Commit Tests
# =============================================================================

class TestTransactionCommit:
    """Tests for transaction commit behavior."""

    def test_commit_applies_changes(self, rejig: Rejig, tmp_python_project: Path):
        """
        commit() should write all pending changes to disk.
        """
        file_path = tmp_python_project / "src" / "models.py"
        original = file_path.read_text()
        new_content = original + "\n# committed change\n"

        with rejig.transaction() as tx:
            tx.add_change(
                path=file_path,
                original=original,
                new_content=new_content,
                operation="add comment",
            )

            result = tx.commit()

            assert isinstance(result, BatchResult)
            assert result.success is True

        # File should now contain the change
        assert file_path.read_text() == new_content

    def test_commit_empty_transaction(self, rejig: Rejig):
        """
        Committing an empty transaction should succeed with a "no changes" message.
        """
        with rejig.transaction() as tx:
            result = tx.commit()

            assert isinstance(result, BatchResult)
            assert result.success is True
            assert len(result.results) == 1
            assert "No changes" in result.results[0].message

    def test_double_commit_returns_error(self, rejig: Rejig, tmp_python_project: Path):
        """
        Committing a transaction twice should return an error.
        """
        file_path = tmp_python_project / "src" / "models.py"
        original = file_path.read_text()

        with rejig.transaction() as tx:
            tx.add_change(
                path=file_path,
                original=original,
                new_content=original + "\n# change\n",
                operation="modify",
            )

            tx.commit()
            result = tx.commit()

            assert isinstance(result, BatchResult)
            assert not result.success

    def test_commit_returns_diffs(self, rejig: Rejig, tmp_python_project: Path):
        """
        commit() should return results with diff information.
        """
        file_path = tmp_python_project / "src" / "models.py"
        original = file_path.read_text()

        with rejig.transaction() as tx:
            tx.add_change(
                path=file_path,
                original=original,
                new_content=original + "\n# new line\n",
                operation="add line",
            )

            result = tx.commit()

            # Should have diffs
            assert result.diffs
            assert file_path in result.diffs

    def test_add_change_after_commit_fails(self, rejig: Rejig, tmp_python_project: Path):
        """
        Adding a change after commit should return an error.
        """
        file_path = tmp_python_project / "src" / "models.py"
        original = file_path.read_text()

        with rejig.transaction() as tx:
            tx.commit()

            result = tx.add_change(
                path=file_path,
                original=original,
                new_content=original + "\n# late change\n",
                operation="late modify",
            )

            assert isinstance(result, ErrorResult)
            assert "finalized" in result.message.lower()


# =============================================================================
# Transaction Rollback Tests
# =============================================================================

class TestTransactionRollback:
    """Tests for transaction rollback behavior."""

    def test_rollback_discards_changes(self, rejig: Rejig, tmp_python_project: Path):
        """
        rollback() should discard all pending changes.
        """
        file_path = tmp_python_project / "src" / "models.py"
        original = file_path.read_text()

        with rejig.transaction() as tx:
            tx.add_change(
                path=file_path,
                original=original,
                new_content=original + "\n# should be discarded\n",
                operation="modify",
            )

            result = tx.rollback()

            assert result.success is True
            assert tx.pending_count == 0

        # File should be unchanged
        assert file_path.read_text() == original

    def test_rollback_after_commit_fails(self, rejig: Rejig, tmp_python_project: Path):
        """
        Rolling back after commit should return an error.
        """
        file_path = tmp_python_project / "src" / "models.py"
        original = file_path.read_text()

        with rejig.transaction() as tx:
            tx.add_change(
                path=file_path,
                original=original,
                new_content=original + "\n# change\n",
                operation="modify",
            )
            tx.commit()

            result = tx.rollback()

            assert isinstance(result, ErrorResult)

    def test_auto_rollback_on_context_exit(self, rejig: Rejig, tmp_python_project: Path):
        """
        If a transaction is not committed, it should be auto-rolled back
        when the context manager exits.
        """
        file_path = tmp_python_project / "src" / "models.py"
        original = file_path.read_text()

        with rejig.transaction() as tx:
            tx.add_change(
                path=file_path,
                original=original,
                new_content=original + "\n# auto-rollback test\n",
                operation="modify",
            )
            # Don't commit or rollback -- let auto-rollback handle it

        # File should be unchanged
        assert file_path.read_text() == original

    def test_add_change_after_rollback_fails(self, rejig: Rejig, tmp_python_project: Path):
        """
        Adding a change after rollback should return an error.
        """
        file_path = tmp_python_project / "src" / "models.py"
        original = file_path.read_text()

        with rejig.transaction() as tx:
            tx.rollback()

            result = tx.add_change(
                path=file_path,
                original=original,
                new_content=original + "\n# late change\n",
                operation="late modify",
            )

            assert isinstance(result, ErrorResult)
            assert "finalized" in result.message.lower()

    def test_commit_after_rollback_fails(self, rejig: Rejig):
        """
        Committing after rollback should return an error.
        """
        with rejig.transaction() as tx:
            tx.rollback()

            result = tx.commit()

            assert isinstance(result, BatchResult)
            assert not result.success


# =============================================================================
# Transaction Dry-Run Tests
# =============================================================================

class TestTransactionDryRun:
    """Tests for transactions in dry-run mode."""

    def test_dry_run_commit_does_not_write(self, rejig_dry_run: Rejig, tmp_python_project: Path):
        """
        In dry-run mode, commit() should NOT write files but still return diffs.
        """
        file_path = tmp_python_project / "src" / "models.py"
        original = file_path.read_text()

        with rejig_dry_run.transaction() as tx:
            tx.add_change(
                path=file_path,
                original=original,
                new_content=original + "\n# dry run change\n",
                operation="dry-run modify",
            )

            result = tx.commit()

            assert isinstance(result, BatchResult)
            assert result.success is True
            assert "[DRY RUN]" in result.results[0].message

        # File should NOT be modified
        assert file_path.read_text() == original


# =============================================================================
# Transaction Content Access Tests
# =============================================================================

class TestTransactionContentAccess:
    """Tests for get_current_content within transactions."""

    def test_get_current_content_returns_pending(self, rejig: Rejig, tmp_python_project: Path):
        """
        get_current_content should return pending content if file has been modified.
        """
        file_path = tmp_python_project / "src" / "models.py"
        original = file_path.read_text()
        new_content = original + "\n# pending\n"

        with rejig.transaction() as tx:
            tx.add_change(
                path=file_path,
                original=original,
                new_content=new_content,
                operation="modify",
            )

            content = tx.get_current_content(file_path)
            assert content == new_content

            tx.rollback()

    def test_get_current_content_returns_disk_for_unmodified(self, rejig: Rejig, tmp_python_project: Path):
        """
        get_current_content should return disk content for unmodified files.
        """
        file_path = tmp_python_project / "src" / "models.py"
        original = file_path.read_text()

        with rejig.transaction() as tx:
            content = tx.get_current_content(file_path)
            assert content == original

            tx.rollback()

    def test_get_current_content_returns_none_for_missing(self, rejig: Rejig, tmp_python_project: Path):
        """
        get_current_content should return None for files that don't exist.
        """
        with rejig.transaction() as tx:
            content = tx.get_current_content(tmp_python_project / "nonexistent.py")
            assert content is None

            tx.rollback()


# =============================================================================
# Transaction Preview Tests
# =============================================================================

class TestTransactionPreview:
    """Tests for transaction preview functionality."""

    def test_preview_shows_diff(self, rejig: Rejig, tmp_python_project: Path):
        """
        preview() should return a combined diff of all pending changes.
        """
        file_path = tmp_python_project / "src" / "models.py"
        original = file_path.read_text()

        with rejig.transaction() as tx:
            tx.add_change(
                path=file_path,
                original=original,
                new_content=original + "\n# preview test\n",
                operation="modify",
            )

            preview = tx.preview()

            assert "# preview test" in preview
            assert "---" in preview
            assert "+++" in preview

            tx.rollback()

    def test_preview_empty_transaction(self, rejig: Rejig):
        """
        preview() on empty transaction should return empty string.
        """
        with rejig.transaction() as tx:
            preview = tx.preview()

            assert preview == ""

            tx.rollback()
