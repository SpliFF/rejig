"""Base classes for the unified Target architecture.

This module defines the core abstractions:
- Target - Base class for all targets (files, modules, classes, functions, etc.)
- ErrorTarget - Sentinel for failed lookups, allows chaining
- TargetList - Batch operations on multiple targets
"""
from __future__ import annotations

import re
from abc import ABC
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Generic, Iterator, TypeVar

from rejig.core.results import BatchResult, ErrorResult, Result

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


__all__ = [
    "Target",
    "ErrorTarget",
    "TargetList",
]


T = TypeVar("T", bound="Target")


class Target(ABC):
    """Base class for all targets - things we can perform operations on.

    Targets never raise exceptions for unsupported or failed operations.
    Instead, they return ErrorResult with details of what went wrong.

    Subclasses should override methods to implement their specific behavior.
    The base implementation returns ErrorResult for all operations.
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig

    @property
    def rejig(self) -> Rejig:
        """Access the parent Rejig instance."""
        return self._rejig

    @property
    def dry_run(self) -> bool:
        """Check if we're in dry-run mode."""
        return self._rejig.dry_run

    def exists(self) -> bool:
        """Check if this target exists in the codebase."""
        raise NotImplementedError

    def get_content(self) -> Result:
        """Get the content/source code of this target."""
        return self._unsupported_operation("get_content")

    def _unsupported_operation(self, operation: str, **context: Any) -> ErrorResult:
        """Return ErrorResult for operations not supported by this target type."""
        return ErrorResult(
            message=f"Operation '{operation}' not supported for {self.__class__.__name__}",
            operation=operation,
            target_repr=repr(self),
        )

    def _operation_failed(
        self,
        operation: str,
        message: str,
        exception: Exception | None = None,
    ) -> ErrorResult:
        """Return ErrorResult for operations that failed during execution."""
        return ErrorResult(
            message=message,
            operation=operation,
            target_repr=repr(self),
            exception=exception,
        )

    def _get_file_content(self, path: Path) -> str | None:
        """Get file content, transaction-aware.

        If in a transaction, returns pending content if available.
        Otherwise reads from disk.

        Parameters
        ----------
        path : Path
            Path to the file.

        Returns
        -------
        str | None
            File content, or None if file doesn't exist.
        """
        tx = self._rejig.current_transaction
        if tx is not None:
            return tx.get_current_content(path)
        if path.exists():
            return path.read_text()
        return None

    def _write_with_diff(
        self,
        path: Path,
        original: str,
        new_content: str,
        operation: str,
    ) -> Result:
        """Write content with diff generation, transaction-aware.

        If in a transaction, the change is recorded but not applied.
        Otherwise writes immediately.

        Parameters
        ----------
        path : Path
            Path to the file.
        original : str
            Original file content.
        new_content : str
            New file content.
        operation : str
            Description of the operation (for messages).

        Returns
        -------
        Result
            Result of the operation with diff included.
        """
        if new_content == original:
            return Result(success=True, message=f"No changes needed for {operation}")

        from rejig.core.diff import generate_diff

        # Check if we're in a transaction
        tx = self._rejig.current_transaction
        if tx is not None:
            return tx.add_change(path, original, new_content, operation)

        # Not in transaction - write immediately
        diff = generate_diff(original, new_content, path)

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would {operation}",
                files_changed=[path],
                diff=diff,
                diffs={path: diff},
            )

        try:
            path.write_text(new_content)
            return Result(
                success=True,
                message=f"Completed {operation}",
                files_changed=[path],
                diff=diff,
                diffs={path: diff},
            )
        except Exception as e:
            return self._operation_failed(operation, f"Write failed: {e}", e)

    # ===== Common operations - subclasses override to implement =====

    def add_function(self, name: str, body: str = "pass", **kwargs: Any) -> Result:
        """Add a function to this target."""
        return self._unsupported_operation("add_function", name=name)

    def add_class(self, name: str, body: str = "pass", **kwargs: Any) -> Result:
        """Add a class to this target."""
        return self._unsupported_operation("add_class", name=name)

    def add_method(self, name: str, body: str = "pass", **kwargs: Any) -> Result:
        """Add a method to this target."""
        return self._unsupported_operation("add_method", name=name)

    def add_attribute(self, name: str, type_hint: str, default: str = "None") -> Result:
        """Add an attribute to this target."""
        return self._unsupported_operation("add_attribute", name=name)

    def add_import(self, import_statement: str) -> Result:
        """Add an import statement to this target."""
        return self._unsupported_operation("add_import", statement=import_statement)

    def add_decorator(self, decorator: str) -> Result:
        """Add a decorator to this target."""
        return self._unsupported_operation("add_decorator", decorator=decorator)

    def remove_decorator(self, decorator: str) -> Result:
        """Remove a decorator from this target."""
        return self._unsupported_operation("remove_decorator", decorator=decorator)

    def rename(self, new_name: str) -> Result:
        """Rename this target."""
        return self._unsupported_operation("rename", new_name=new_name)

    def delete(self) -> Result:
        """Delete this target."""
        return self._unsupported_operation("delete")

    def move_to(self, destination: str | Target) -> Result:
        """Move this target to a new location."""
        return self._unsupported_operation("move_to", destination=str(destination))

    def insert_statement(self, statement: str, position: str = "start") -> Result:
        """Insert a statement into this target."""
        return self._unsupported_operation("insert_statement", statement=statement)

    def insert_before(self, content: str) -> Result:
        """Insert content before this target."""
        return self._unsupported_operation("insert_before")

    def insert_after(self, content: str) -> Result:
        """Insert content after this target."""
        return self._unsupported_operation("insert_after")

    def rewrite(self, new_content: str) -> Result:
        """Replace the content of this target."""
        return self._unsupported_operation("rewrite")

    def replace(self, pattern: str, replacement: str) -> Result:
        """Replace pattern in this target's content."""
        return self._unsupported_operation("replace")

    # ===== Navigation methods - return new Target or TargetList =====

    def find_class(self, name: str) -> Target:
        """Find a class within this target. Returns ErrorTarget if not supported."""
        return ErrorTarget(self._rejig, f"find_class not supported for {self.__class__.__name__}")

    def find_function(self, name: str) -> Target:
        """Find a function within this target. Returns ErrorTarget if not supported."""
        return ErrorTarget(self._rejig, f"find_function not supported for {self.__class__.__name__}")

    def find_method(self, name: str) -> Target:
        """Find a method within this target. Returns ErrorTarget if not supported."""
        return ErrorTarget(self._rejig, f"find_method not supported for {self.__class__.__name__}")

    def find_classes(self, pattern: str | None = None) -> TargetList[Target]:
        """Find all classes within this target."""
        return TargetList(self._rejig, [])

    def find_functions(self, pattern: str | None = None) -> TargetList[Target]:
        """Find all functions within this target."""
        return TargetList(self._rejig, [])

    def find_methods(self, pattern: str | None = None) -> TargetList[Target]:
        """Find all methods within this target."""
        return TargetList(self._rejig, [])

    def line(self, line_number: int) -> Target:
        """Get a specific line of this target. Returns ErrorTarget if not supported."""
        return ErrorTarget(self._rejig, f"line not supported for {self.__class__.__name__}")

    def lines(self, start: int, end: int) -> Target:
        """Get a range of lines of this target. Returns ErrorTarget if not supported."""
        return ErrorTarget(self._rejig, f"lines not supported for {self.__class__.__name__}")


class ErrorTarget(Target):
    """A target that represents a failed lookup - all operations return ErrorResult.

    Navigation methods return ErrorTarget (not ErrorResult) to allow chaining.
    Operation methods return ErrorResult.

    This allows code like:
        rj.module("nonexistent").find_class("Foo").add_method("bar")
    to return an ErrorResult without raising, even though the module doesn't exist.
    """

    def __init__(self, rejig: Rejig, error_message: str) -> None:
        super().__init__(rejig)
        self._error_message = error_message

    def exists(self) -> bool:
        return False

    def __repr__(self) -> str:
        return f"ErrorTarget({self._error_message!r})"

    # Navigation methods return ErrorTarget to allow chaining
    def find_class(self, name: str) -> ErrorTarget:
        return self

    def find_function(self, name: str) -> ErrorTarget:
        return self

    def find_method(self, name: str) -> ErrorTarget:
        return self

    def find_classes(self, pattern: str | None = None) -> TargetList[Target]:
        return TargetList(self._rejig, [])

    def find_functions(self, pattern: str | None = None) -> TargetList[Target]:
        return TargetList(self._rejig, [])

    def find_methods(self, pattern: str | None = None) -> TargetList[Target]:
        return TargetList(self._rejig, [])

    def line(self, line_number: int) -> ErrorTarget:
        return self

    def lines(self, start: int, end: int) -> ErrorTarget:
        return self

    def __getattr__(self, name: str) -> Callable[..., ErrorResult]:
        """Any other method call returns an ErrorResult."""

        def error_method(*args: Any, **kwargs: Any) -> ErrorResult:
            return ErrorResult(
                message=self._error_message,
                operation=name,
                target_repr="ErrorTarget",
            )

        return error_method


class TargetList(Generic[T]):
    """A list of targets that can be operated on uniformly.

    Operations are applied to all targets, returning a BatchResult.
    This class is also returned by find operations (e.g., find_classes(), find_functions()).

    Example:
        all_classes = rj.find_classes(pattern="^Test")
        results = all_classes.add_decorator("pytest.mark.slow")
        if results.partial_success:
            print(f"Modified {len(results.succeeded)} classes")
    """

    def __init__(self, rejig: Rejig, targets: list[T]) -> None:
        self._rejig = rejig
        self._targets = targets

    def __iter__(self) -> Iterator[T]:
        return iter(self._targets)

    def __len__(self) -> int:
        return len(self._targets)

    def __bool__(self) -> bool:
        return len(self._targets) > 0

    def __getitem__(self, index: int) -> T:
        return self._targets[index]

    def __repr__(self) -> str:
        return f"TargetList({len(self._targets)} targets)"

    # ===== Filtering methods =====

    def filter(self, predicate: Callable[[T], bool]) -> TargetList[T]:
        """Filter targets by a predicate."""
        return TargetList(self._rejig, [t for t in self._targets if predicate(t)])

    def in_file(self, path: Path | str) -> TargetList[T]:
        """Filter to targets in a specific file."""
        path = Path(path) if isinstance(path, str) else path
        return self.filter(lambda t: hasattr(t, "file_path") and t.file_path == path)

    def matching(self, pattern: str) -> TargetList[T]:
        """Filter to targets whose name matches a regex pattern."""
        regex = re.compile(pattern)
        return self.filter(lambda t: hasattr(t, "name") and regex.search(t.name or ""))

    def first(self) -> T | None:
        """Get the first target, or None if empty."""
        return self._targets[0] if self._targets else None

    def last(self) -> T | None:
        """Get the last target, or None if empty."""
        return self._targets[-1] if self._targets else None

    def to_list(self) -> list[T]:
        """Return the underlying list of targets."""
        return list(self._targets)

    # ===== Batch operations - apply to all targets, return BatchResult =====

    def add_decorator(self, decorator: str) -> BatchResult:
        """Add a decorator to all targets."""
        return BatchResult([t.add_decorator(decorator) for t in self._targets])

    def remove_decorator(self, decorator: str) -> BatchResult:
        """Remove a decorator from all targets."""
        return BatchResult([t.remove_decorator(decorator) for t in self._targets])

    def rename(self, pattern: str, replacement: str) -> BatchResult:
        """Rename all targets using pattern substitution."""
        results: list[Result] = []
        for t in self._targets:
            if hasattr(t, "name") and t.name:
                new_name = re.sub(pattern, replacement, t.name)
                results.append(t.rename(new_name))
            else:
                results.append(
                    ErrorResult(
                        message="Target has no name attribute",
                        operation="rename",
                        target_repr=repr(t),
                    )
                )
        return BatchResult(results)

    def delete(self) -> BatchResult:
        """Delete all targets."""
        return BatchResult([t.delete() for t in self._targets])

    def delete_all(self) -> BatchResult:
        """Alias for delete()."""
        return self.delete()

    def insert_statement(self, statement: str, position: str = "start") -> BatchResult:
        """Insert a statement in all targets."""
        return BatchResult([t.insert_statement(statement, position) for t in self._targets])

    def add_decorator_all(self, decorator: str) -> BatchResult:
        """Alias for add_decorator()."""
        return self.add_decorator(decorator)

    def rename_all(self, pattern: str, replacement: str) -> BatchResult:
        """Alias for rename()."""
        return self.rename(pattern, replacement)

    def replace_all(self, pattern: str, replacement: str) -> BatchResult:
        """Replace pattern in all targets that support it."""
        results: list[Result] = []
        for t in self._targets:
            if hasattr(t, "replace"):
                results.append(t.replace(pattern, replacement))
            else:
                results.append(
                    ErrorResult(
                        message=f"Operation 'replace' not supported for {t.__class__.__name__}",
                        operation="replace",
                        target_repr=repr(t),
                    )
                )
        return BatchResult(results)

    # ===== Type hint batch operations =====

    def modernize_type_hints(self) -> BatchResult:
        """Modernize type hints in all targets (FileTarget).

        Converts old-style type hints to Python 3.10+ syntax:
        - List[str] → list[str]
        - Dict[str, int] → dict[str, int]
        - Optional[str] → str | None
        - Union[str, int] → str | int

        Returns
        -------
        BatchResult
            Results of all operations.

        Examples
        --------
        >>> files = rj.find_files("**/*.py")
        >>> files.modernize_type_hints()
        """
        results: list[Result] = []
        for t in self._targets:
            if hasattr(t, "modernize_type_hints"):
                results.append(t.modernize_type_hints())
            else:
                results.append(
                    ErrorResult(
                        message=f"Operation 'modernize_type_hints' not supported for {t.__class__.__name__}",
                        operation="modernize_type_hints",
                        target_repr=repr(t),
                    )
                )
        return BatchResult(results)

    def convert_type_comments(self) -> BatchResult:
        """Convert type comments to inline annotations in all targets.

        Converts:
            x = 1  # type: int
        To:
            x: int = 1

        Returns
        -------
        BatchResult
            Results of all operations.

        Examples
        --------
        >>> files = rj.find_files("**/*.py")
        >>> files.convert_type_comments()
        """
        results: list[Result] = []
        for t in self._targets:
            if hasattr(t, "convert_type_comments_to_annotations"):
                results.append(t.convert_type_comments_to_annotations())
            else:
                results.append(
                    ErrorResult(
                        message=f"Operation 'convert_type_comments' not supported for {t.__class__.__name__}",
                        operation="convert_type_comments",
                        target_repr=repr(t),
                    )
                )
        return BatchResult(results)

    def infer_type_hints(self, overwrite: bool = False) -> BatchResult:
        """Infer and add type hints to all targets (FunctionTarget/MethodTarget).

        Uses heuristics to infer types from:
        - Default parameter values (e.g., = 0 → int)
        - Parameter names (e.g., count → int, is_valid → bool)

        Parameters
        ----------
        overwrite : bool
            If True, overwrite existing type hints. Default False.

        Returns
        -------
        BatchResult
            Results of all operations.

        Examples
        --------
        >>> funcs = rj.find_functions()
        >>> funcs.infer_type_hints()
        """
        results: list[Result] = []
        for t in self._targets:
            if hasattr(t, "infer_type_hints"):
                results.append(t.infer_type_hints(overwrite))
            else:
                results.append(
                    ErrorResult(
                        message=f"Operation 'infer_type_hints' not supported for {t.__class__.__name__}",
                        operation="infer_type_hints",
                        target_repr=repr(t),
                    )
                )
        return BatchResult(results)

    def remove_type_hints(self) -> BatchResult:
        """Remove type hints from all targets (FunctionTarget/MethodTarget).

        Removes return type annotations and parameter type annotations.

        Returns
        -------
        BatchResult
            Results of all operations.

        Examples
        --------
        >>> funcs = rj.find_functions("^test_")
        >>> funcs.remove_type_hints()
        """
        results: list[Result] = []
        for t in self._targets:
            if hasattr(t, "remove_type_hints"):
                results.append(t.remove_type_hints())
            else:
                results.append(
                    ErrorResult(
                        message=f"Operation 'remove_type_hints' not supported for {t.__class__.__name__}",
                        operation="remove_type_hints",
                        target_repr=repr(t),
                    )
                )
        return BatchResult(results)

    # ===== Docstring batch operations =====

    def generate_docstrings(
        self,
        style: str = "google",
        overwrite: bool = False,
    ) -> BatchResult:
        """Generate docstrings for all targets (FunctionTarget/MethodTarget/ClassTarget).

        Creates docstrings from function/method signatures including
        parameters, return type, and raised exceptions.

        Parameters
        ----------
        style : str
            Docstring style: "google", "numpy", or "sphinx".
            Defaults to "google".
        overwrite : bool
            Whether to overwrite existing docstrings. Default False.

        Returns
        -------
        BatchResult
            Results of all operations.

        Examples
        --------
        >>> funcs = rj.find_functions()
        >>> funcs.generate_docstrings()
        >>> methods = cls.find_methods()
        >>> methods.generate_docstrings(style="numpy")
        """
        results: list[Result] = []
        for t in self._targets:
            if hasattr(t, "generate_docstring"):
                results.append(t.generate_docstring(style=style, overwrite=overwrite))
            elif hasattr(t, "generate_docstrings"):
                results.append(t.generate_docstrings(style=style, overwrite=overwrite))
            else:
                results.append(
                    ErrorResult(
                        message=f"Operation 'generate_docstrings' not supported for {t.__class__.__name__}",
                        operation="generate_docstrings",
                        target_repr=repr(t),
                    )
                )
        return BatchResult(results)

    def without_docstrings(self) -> TargetList[T]:
        """Filter to targets that don't have docstrings.

        Returns
        -------
        TargetList[T]
            List of targets without docstrings.

        Examples
        --------
        >>> funcs = rj.find_functions()
        >>> no_docs = funcs.without_docstrings()
        >>> no_docs.generate_docstrings()
        """
        def has_no_docstring(t: T) -> bool:
            if hasattr(t, "has_docstring"):
                return not t.has_docstring
            return False

        return self.filter(has_no_docstring)

    def with_docstrings(self) -> TargetList[T]:
        """Filter to targets that have docstrings.

        Returns
        -------
        TargetList[T]
            List of targets with docstrings.

        Examples
        --------
        >>> funcs = rj.find_functions()
        >>> with_docs = funcs.with_docstrings()
        """
        def has_docstring(t: T) -> bool:
            if hasattr(t, "has_docstring"):
                return t.has_docstring
            return False

        return self.filter(has_docstring)

    def convert_docstring_style(
        self,
        from_style: str | None,
        to_style: str,
    ) -> BatchResult:
        """Convert docstring style for all targets (FileTarget).

        Parameters
        ----------
        from_style : str | None
            Source docstring style ("google", "numpy", "sphinx"),
            or None to auto-detect.
        to_style : str
            Target docstring style ("google", "numpy", "sphinx").

        Returns
        -------
        BatchResult
            Results of all operations.

        Examples
        --------
        >>> files = rj.find_files("**/*.py")
        >>> files.convert_docstring_style("sphinx", "google")
        """
        results: list[Result] = []
        for t in self._targets:
            if hasattr(t, "convert_docstring_style"):
                results.append(t.convert_docstring_style(from_style, to_style))
            else:
                results.append(
                    ErrorResult(
                        message=f"Operation 'convert_docstring_style' not supported for {t.__class__.__name__}",
                        operation="convert_docstring_style",
                        target_repr=repr(t),
                    )
                )
        return BatchResult(results)

    def generate_all_docstrings(
        self,
        style: str = "google",
        overwrite: bool = False,
    ) -> BatchResult:
        """Generate all docstrings for all targets (FileTarget).

        This generates docstrings for all functions and methods in the files.

        Parameters
        ----------
        style : str
            Docstring style: "google", "numpy", or "sphinx".
            Defaults to "google".
        overwrite : bool
            Whether to overwrite existing docstrings. Default False.

        Returns
        -------
        BatchResult
            Results of all operations.

        Examples
        --------
        >>> files = rj.find_files("**/*.py")
        >>> files.generate_all_docstrings()
        """
        results: list[Result] = []
        for t in self._targets:
            if hasattr(t, "generate_all_docstrings"):
                results.append(t.generate_all_docstrings(style=style, overwrite=overwrite))
            else:
                results.append(
                    ErrorResult(
                        message=f"Operation 'generate_all_docstrings' not supported for {t.__class__.__name__}",
                        operation="generate_all_docstrings",
                        target_repr=repr(t),
                    )
                )
        return BatchResult(results)
