"""Base classes for the unified Target architecture.

This module defines the core abstractions:
- Result / ErrorResult / BatchResult - Operation results (never raise exceptions)
- Target - Base class for all targets (files, modules, classes, functions, etc.)
- ErrorTarget - Sentinel for failed lookups, allows chaining
- TargetList - Batch operations on multiple targets
"""
from __future__ import annotations

import re
from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Generic, Iterator, TypeVar

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


@dataclass
class Result:
    """Base result for all operations.

    Operations never raise exceptions. Instead, they return Result objects
    that indicate success or failure.

    Attributes:
        success: Whether the operation succeeded
        message: Human-readable description of what happened
        files_changed: List of files that were modified
        data: Optional payload for operations that return data
    """

    success: bool
    message: str
    files_changed: list[Path] = field(default_factory=list)
    data: Any = None

    def __bool__(self) -> bool:
        return self.success

    def is_error(self) -> bool:
        """Check if this result represents an error."""
        return not self.success


@dataclass
class ErrorResult(Result):
    """Result for failed operations - never raises automatically.

    Attributes:
        exception: The original exception, if any
        operation: Name of the attempted operation
        target_repr: String representation of the target
    """

    success: bool = field(default=False, init=False)
    exception: Exception | None = None
    operation: str = ""
    target_repr: str = ""

    def raise_if_error(self) -> None:
        """Explicitly re-raise the exception if the programmer wants to."""
        if self.exception:
            raise self.exception
        raise RuntimeError(self.message)


@dataclass
class BatchResult:
    """Aggregate result for operations applied to multiple targets.

    Used by TargetList when performing batch operations.
    """

    results: list[Result] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True if all operations succeeded."""
        return all(r.success for r in self.results)

    @property
    def partial_success(self) -> bool:
        """True if at least one operation succeeded."""
        return any(r.success for r in self.results)

    @property
    def all_failed(self) -> bool:
        """True if all operations failed."""
        return all(not r.success for r in self.results)

    @property
    def succeeded(self) -> list[Result]:
        """Results that succeeded."""
        return [r for r in self.results if r.success]

    @property
    def failed(self) -> list[Result]:
        """Results that failed."""
        return [r for r in self.results if not r.success]

    @property
    def files_changed(self) -> list[Path]:
        """All files changed across all operations."""
        files: list[Path] = []
        for r in self.results:
            files.extend(r.files_changed)
        return list(set(files))

    def __bool__(self) -> bool:
        return self.success

    def __len__(self) -> int:
        return len(self.results)

    def __iter__(self) -> Iterator[Result]:
        return iter(self.results)


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
    This class also serves as the result type for find operations (replacing FindResult).

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
