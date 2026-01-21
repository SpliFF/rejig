"""
Tests for rejig.core.results module.

This module tests the Result, ErrorResult, and BatchResult classes which form
the foundation of Rejig's error handling strategy. Operations never raise
exceptions - they return Result objects instead.

Coverage targets:
- Result: success/failure states, boolean evaluation, diff access
- ErrorResult: error details, raise_if_error behavior
- BatchResult: aggregation, filtering, iteration, diff merging
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rejig.core.results import BatchResult, ErrorResult, Result


# =============================================================================
# Result Tests
# =============================================================================

class TestResult:
    """Tests for the base Result class."""

    def test_successful_result_creation(self):
        """
        A successful Result should have success=True and be truthy.
        This is the standard way to indicate an operation completed successfully.
        """
        result = Result(success=True, message="Operation completed")

        # success attribute should be True
        assert result.success is True
        # Result should be truthy when used in boolean context
        assert bool(result) is True
        # is_error should return False for successful results
        assert result.is_error() is False
        # Message should be preserved
        assert result.message == "Operation completed"

    def test_failed_result_creation(self):
        """
        A failed Result should have success=False and be falsy.
        This indicates an operation that did not complete as expected.
        """
        result = Result(success=False, message="Operation failed")

        # success attribute should be False
        assert result.success is False
        # Result should be falsy when used in boolean context
        assert bool(result) is False
        # is_error should return True for failed results
        assert result.is_error() is True

    def test_result_with_files_changed(self):
        """
        Result should track which files were modified during the operation.
        This is important for reporting and undo operations.
        """
        files = [Path("/tmp/file1.py"), Path("/tmp/file2.py")]
        result = Result(success=True, message="Modified files", files_changed=files)

        # files_changed should contain the paths
        assert len(result.files_changed) == 2
        assert Path("/tmp/file1.py") in result.files_changed
        assert Path("/tmp/file2.py") in result.files_changed

    def test_result_with_data_payload(self):
        """
        Result can carry arbitrary data payload for operations that return data.
        For example, get_content() returns the content in the data field.
        """
        data = {"key": "value", "count": 42}
        result = Result(success=True, message="Data retrieved", data=data)

        # data should be accessible
        assert result.data == {"key": "value", "count": 42}
        assert result.data["count"] == 42

    def test_result_with_diff(self):
        """
        Result should carry diff information showing what changed.
        The diff field contains the combined diff, diffs contains per-file diffs.
        """
        diff_content = "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new"
        path = Path("/tmp/file.py")

        result = Result(
            success=True,
            message="File modified",
            files_changed=[path],
            diff=diff_content,
            diffs={path: diff_content},
        )

        # Combined diff should be accessible
        assert result.diff == diff_content
        # Per-file diff should be accessible via get_diff
        assert result.get_diff(path) == diff_content
        # get_diff with no argument returns combined diff
        assert result.get_diff() == diff_content

    def test_result_get_diff_missing_file(self):
        """
        get_diff should return None for files that weren't changed.
        """
        result = Result(success=True, message="Done")

        # Should return None for non-existent path
        assert result.get_diff(Path("/nonexistent.py")) is None
        # Should return None if no diff at all
        assert result.get_diff() is None

    def test_result_default_values(self):
        """
        Result should have sensible defaults for optional fields.
        """
        result = Result(success=True, message="Test")

        # Default empty list for files_changed
        assert result.files_changed == []
        # Default None for data
        assert result.data is None
        # Default None for diff
        assert result.diff is None
        # Default empty dict for diffs
        assert result.diffs == {}


# =============================================================================
# ErrorResult Tests
# =============================================================================

class TestErrorResult:
    """Tests for the ErrorResult class - represents failed operations."""

    def test_error_result_always_unsuccessful(self):
        """
        ErrorResult should always have success=False, regardless of any attempt
        to set it otherwise. This is enforced at the dataclass level.
        """
        # Note: success is not an init parameter for ErrorResult
        error = ErrorResult(message="Something went wrong")

        # success should always be False
        assert error.success is False
        # Should be falsy in boolean context
        assert bool(error) is False
        # is_error should return True
        assert error.is_error() is True

    def test_error_result_with_exception(self):
        """
        ErrorResult can store the original exception for debugging.
        This allows callers to inspect or re-raise if needed.
        """
        original_exception = ValueError("Invalid input")
        error = ErrorResult(
            message="Operation failed: Invalid input",
            exception=original_exception,
        )

        # Exception should be stored
        assert error.exception is original_exception
        assert isinstance(error.exception, ValueError)
        assert str(error.exception) == "Invalid input"

    def test_error_result_with_operation_context(self):
        """
        ErrorResult should store context about what operation was attempted.
        This helps with debugging and error reporting.
        """
        error = ErrorResult(
            message="Class not found",
            operation="find_class",
            target_repr="FileTarget('src/models.py')",
        )

        # Context should be preserved
        assert error.operation == "find_class"
        assert error.target_repr == "FileTarget('src/models.py')"

    def test_error_result_raise_if_error_with_exception(self):
        """
        raise_if_error() should re-raise the original exception if present.
        This allows callers to opt into exception-based error handling.
        """
        original = ValueError("Test error")
        error = ErrorResult(message="Failed", exception=original)

        # Should raise the original exception
        with pytest.raises(ValueError) as exc_info:
            error.raise_if_error()

        assert exc_info.value is original

    def test_error_result_raise_if_error_without_exception(self):
        """
        raise_if_error() should raise RuntimeError if no original exception.
        The message should be included in the RuntimeError.
        """
        error = ErrorResult(message="Operation failed for unknown reason")

        # Should raise RuntimeError with the message
        with pytest.raises(RuntimeError) as exc_info:
            error.raise_if_error()

        assert "Operation failed for unknown reason" in str(exc_info.value)

    def test_error_result_inherits_from_result(self):
        """
        ErrorResult should inherit from Result and support all Result methods.
        """
        error = ErrorResult(message="Error")

        # Should have all Result attributes
        assert hasattr(error, "files_changed")
        assert hasattr(error, "data")
        assert hasattr(error, "diff")
        assert hasattr(error, "diffs")
        assert hasattr(error, "get_diff")


# =============================================================================
# BatchResult Tests
# =============================================================================

class TestBatchResult:
    """Tests for BatchResult - aggregates results from batch operations."""

    def test_empty_batch_result(self):
        """
        Empty BatchResult behavior with vacuous truth for all() and any().

        In Python, all() on empty iterable returns True (vacuous truth),
        and any() on empty iterable returns False. This affects our properties:
        - success (all succeeded): True (vacuous truth)
        - partial_success (any succeeded): False
        - all_failed (all failed): True (vacuous truth)

        The __bool__ follows success, so empty batch is truthy.
        """
        batch = BatchResult()

        # all() on empty list returns True (vacuous truth)
        # So success is True for empty batch
        assert batch.success is True
        # any() on empty list returns False
        # So partial_success is False for empty batch
        assert batch.partial_success is False
        # all(not x) on empty list returns True (vacuous truth)
        # So all_failed is True for empty batch
        assert batch.all_failed is True
        # Length should be 0
        assert len(batch) == 0
        # __bool__ follows success, so empty batch is truthy
        assert bool(batch) is True

    def test_batch_result_all_success(self):
        """
        BatchResult with all successful results should indicate full success.
        """
        results = [
            Result(success=True, message="Op 1"),
            Result(success=True, message="Op 2"),
            Result(success=True, message="Op 3"),
        ]
        batch = BatchResult(results=results)

        # All succeeded, so success is True
        assert batch.success is True
        # At least one succeeded
        assert batch.partial_success is True
        # Not all failed
        assert batch.all_failed is False
        # Length should match
        assert len(batch) == 3
        # Should be truthy
        assert bool(batch) is True

    def test_batch_result_all_failed(self):
        """
        BatchResult with all failed results should indicate total failure.
        """
        results = [
            Result(success=False, message="Op 1 failed"),
            Result(success=False, message="Op 2 failed"),
        ]
        batch = BatchResult(results=results)

        # Not all succeeded
        assert batch.success is False
        # No successes
        assert batch.partial_success is False
        # All failed
        assert batch.all_failed is True
        # Should be falsy
        assert bool(batch) is False

    def test_batch_result_partial_success(self):
        """
        BatchResult with mixed results should indicate partial success.
        """
        results = [
            Result(success=True, message="Op 1 ok"),
            Result(success=False, message="Op 2 failed"),
            Result(success=True, message="Op 3 ok"),
        ]
        batch = BatchResult(results=results)

        # Not all succeeded
        assert batch.success is False
        # At least one succeeded
        assert batch.partial_success is True
        # Not all failed
        assert batch.all_failed is False

    def test_batch_result_succeeded_filter(self):
        """
        succeeded property should return only successful results.
        """
        results = [
            Result(success=True, message="Success 1"),
            Result(success=False, message="Failure"),
            Result(success=True, message="Success 2"),
        ]
        batch = BatchResult(results=results)

        succeeded = batch.succeeded

        # Should have 2 successful results
        assert len(succeeded) == 2
        # All should be successful
        assert all(r.success for r in succeeded)
        # Messages should match
        assert succeeded[0].message == "Success 1"
        assert succeeded[1].message == "Success 2"

    def test_batch_result_failed_filter(self):
        """
        failed property should return only failed results.
        """
        results = [
            Result(success=True, message="Success"),
            Result(success=False, message="Failure 1"),
            Result(success=False, message="Failure 2"),
        ]
        batch = BatchResult(results=results)

        failed = batch.failed

        # Should have 2 failed results
        assert len(failed) == 2
        # All should be failures
        assert all(not r.success for r in failed)

    def test_batch_result_files_changed_aggregation(self):
        """
        files_changed should aggregate all changed files from all results.
        Duplicates should be removed.
        """
        file1 = Path("/tmp/file1.py")
        file2 = Path("/tmp/file2.py")
        file3 = Path("/tmp/file3.py")

        results = [
            Result(success=True, message="Op 1", files_changed=[file1, file2]),
            Result(success=True, message="Op 2", files_changed=[file2, file3]),  # file2 duplicate
        ]
        batch = BatchResult(results=results)

        changed = batch.files_changed

        # Should have 3 unique files
        assert len(changed) == 3
        assert file1 in changed
        assert file2 in changed
        assert file3 in changed

    def test_batch_result_iteration(self):
        """
        BatchResult should be iterable, yielding individual results.
        """
        results = [
            Result(success=True, message="Op 1"),
            Result(success=True, message="Op 2"),
        ]
        batch = BatchResult(results=results)

        # Should be iterable
        iterated = list(batch)
        assert len(iterated) == 2
        assert iterated[0].message == "Op 1"
        assert iterated[1].message == "Op 2"

    def test_batch_result_access_via_results_attribute(self):
        """
        BatchResult provides access to individual results via the results attribute.

        Note: BatchResult does NOT support direct indexing (batch[0]).
        To access individual results, use batch.results[index] or iterate.
        """
        results = [
            Result(success=True, message="First"),
            Result(success=True, message="Second"),
            Result(success=True, message="Third"),
        ]
        batch = BatchResult(results=results)

        # Access via results attribute
        assert batch.results[0].message == "First"
        assert batch.results[1].message == "Second"
        assert batch.results[2].message == "Third"

        # Can also convert to list via iteration
        as_list = list(batch)
        assert as_list[0].message == "First"

    def test_batch_result_diffs_merged(self):
        """
        diffs property should merge all per-file diffs from all results.
        """
        file1 = Path("/tmp/file1.py")
        file2 = Path("/tmp/file2.py")
        diff1 = "--- a/file1.py\n+++ b/file1.py"
        diff2 = "--- a/file2.py\n+++ b/file2.py"

        results = [
            Result(success=True, message="Op 1", diffs={file1: diff1}),
            Result(success=True, message="Op 2", diffs={file2: diff2}),
        ]
        batch = BatchResult(results=results)

        diffs = batch.diffs

        # Should contain both diffs
        assert file1 in diffs
        assert file2 in diffs
        assert diffs[file1] == diff1
        assert diffs[file2] == diff2

    def test_batch_result_get_diff_specific_file(self):
        """
        get_diff(path) should return the diff for that specific file.
        """
        file1 = Path("/tmp/file1.py")
        diff1 = "--- a/file1.py\n+++ b/file1.py\n-old\n+new"

        results = [
            Result(success=True, message="Op", diffs={file1: diff1}),
        ]
        batch = BatchResult(results=results)

        # Should return specific file diff
        assert batch.get_diff(file1) == diff1
        # Should return None for non-existent file
        assert batch.get_diff(Path("/nonexistent.py")) is None

    def test_batch_result_with_error_results(self):
        """
        BatchResult should handle ErrorResult objects correctly.
        """
        results = [
            Result(success=True, message="Success"),
            ErrorResult(message="Error occurred", operation="test"),
        ]
        batch = BatchResult(results=results)

        # Should have partial success
        assert batch.partial_success is True
        # Overall should be failure
        assert batch.success is False
        # failed should contain the ErrorResult
        assert len(batch.failed) == 1
        assert isinstance(batch.failed[0], ErrorResult)


# =============================================================================
# Integration Tests
# =============================================================================

class TestResultIntegration:
    """Integration tests for Result classes working together."""

    def test_result_chain_in_batch(self):
        """
        Test typical usage pattern: multiple operations creating a BatchResult.
        """
        # Simulate a batch operation on multiple files
        results = []
        for i in range(5):
            if i % 2 == 0:
                results.append(Result(
                    success=True,
                    message=f"Modified file{i}.py",
                    files_changed=[Path(f"/tmp/file{i}.py")],
                ))
            else:
                results.append(ErrorResult(
                    message=f"File file{i}.py not found",
                    operation="modify",
                ))

        batch = BatchResult(results=results)

        # Should have 3 successes, 2 failures
        assert len(batch.succeeded) == 3
        assert len(batch.failed) == 2
        # Should have 3 files changed
        assert len(batch.files_changed) == 3

    def test_error_result_in_conditional_flow(self):
        """
        Test typical usage: check result and handle error case.
        """
        def operation_that_might_fail(succeed: bool) -> Result:
            if succeed:
                return Result(success=True, message="Done")
            return ErrorResult(message="Failed", operation="test_op")

        # Success case
        result = operation_that_might_fail(True)
        if result:  # Should enter this branch
            assert result.message == "Done"

        # Failure case
        result = operation_that_might_fail(False)
        if not result:  # Should enter this branch
            assert isinstance(result, ErrorResult)
            assert result.operation == "test_op"
