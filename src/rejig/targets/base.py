"""Base classes for the unified Target architecture.

This module defines the core abstractions:
- Target - Base class for all targets (files, modules, classes, functions, etc.)
- ErrorTarget - Sentinel for failed lookups, allows chaining
- TargetList - Batch operations on multiple targets
- FindingTarget - Base class for finding-based targets (analysis, security, optimize)
- FindingTargetList - Base class for finding-based target lists
"""
from __future__ import annotations

import re
from abc import ABC
from enum import Enum
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Iterator,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from rejig.core.results import BatchResult, ErrorResult, Result

if TYPE_CHECKING:
    from typing import Self

    from rejig.core.rejig import Rejig


__all__ = [
    "Target",
    "ErrorTarget",
    "TargetList",
    "BaseFinding",
    "FindingTarget",
    "FindingTargetList",
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
        """Check if this target exists in the codebase.

        Default implementation returns False. Subclasses should override
        to provide proper existence checking.

        Returns
        -------
        bool
            True if the target exists, False otherwise.
        """
        return False

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

    # ===== Header batch operations =====

    def add_copyright_header(
        self,
        copyright_text: str,
        year: int | None = None,
    ) -> BatchResult:
        """Add a copyright header to all file targets.

        Parameters
        ----------
        copyright_text : str
            Copyright holder text (e.g., "MyCompany Inc.").
        year : int | None
            Copyright year. Defaults to current year.

        Returns
        -------
        BatchResult
            Results of all operations.

        Examples
        --------
        >>> files = rj.find_files("**/*.py")
        >>> files.add_copyright_header("MyCompany Inc.")
        """
        results: list[Result] = []
        for t in self._targets:
            if hasattr(t, "add_copyright_header"):
                results.append(t.add_copyright_header(copyright_text, year))
            else:
                results.append(
                    ErrorResult(
                        message=f"Operation 'add_copyright_header' not supported for {t.__class__.__name__}",
                        operation="add_copyright_header",
                        target_repr=repr(t),
                    )
                )
        return BatchResult(results)

    def add_license_header(
        self,
        license_name: str,
        copyright_holder: str | None = None,
        year: int | None = None,
    ) -> BatchResult:
        """Add a license header to all file targets.

        Parameters
        ----------
        license_name : str
            License identifier: "MIT", "Apache-2.0", "GPL-3.0",
            "BSD-3-Clause", or "Proprietary".
        copyright_holder : str | None
            Copyright holder name. If None, uses a placeholder.
        year : int | None
            Copyright year. Defaults to current year.

        Returns
        -------
        BatchResult
            Results of all operations.

        Examples
        --------
        >>> files = rj.find_files("**/*.py")
        >>> files.add_license_header("MIT")
        """
        results: list[Result] = []
        for t in self._targets:
            if hasattr(t, "add_license_header"):
                results.append(t.add_license_header(license_name, copyright_holder, year))
            else:
                results.append(
                    ErrorResult(
                        message=f"Operation 'add_license_header' not supported for {t.__class__.__name__}",
                        operation="add_license_header",
                        target_repr=repr(t),
                    )
                )
        return BatchResult(results)

    def update_copyright_year(self, new_year: int | None = None) -> BatchResult:
        """Update the copyright year in all file targets.

        Updates patterns like:
        - "Copyright 2023" -> "Copyright 2023-2024"
        - "Copyright 2023-2024" -> "Copyright 2023-2025"

        Parameters
        ----------
        new_year : int | None
            Target year. Defaults to current year.

        Returns
        -------
        BatchResult
            Results of all operations.

        Examples
        --------
        >>> files = rj.find_files("**/*.py")
        >>> files.update_copyright_year()
        """
        results: list[Result] = []
        for t in self._targets:
            if hasattr(t, "update_copyright_year"):
                results.append(t.update_copyright_year(new_year))
            else:
                results.append(
                    ErrorResult(
                        message=f"Operation 'update_copyright_year' not supported for {t.__class__.__name__}",
                        operation="update_copyright_year",
                        target_repr=repr(t),
                    )
                )
        return BatchResult(results)


# =============================================================================
# Finding-based Target Architecture
# =============================================================================
# These base classes provide shared functionality for analysis, security,
# and optimization target systems, reducing code duplication.

# Type variables for finding-based targets
F = TypeVar("F", bound="BaseFinding")  # Finding type
E = TypeVar("E", bound=Enum)  # Enum type for finding types
FT = TypeVar("FT", bound="FindingTarget")  # FindingTarget subclass


@runtime_checkable
class BaseFinding(Protocol):
    """Protocol defining the interface for finding dataclasses.

    All finding types (AnalysisFinding, SecurityFinding, OptimizeFinding)
    must implement these attributes.
    """

    type: Enum
    file_path: Path
    line_number: int
    name: str | None
    message: str
    severity: str
    context: dict

    @property
    def location(self) -> str:
        """Return a formatted location string."""
        ...


class FindingTarget(Target, Generic[F]):
    """Base class for finding-based targets.

    Provides common properties and methods for targets that wrap findings
    (AnalysisTarget, SecurityTarget, OptimizeTarget).

    Type Parameters
    ---------------
    F : BaseFinding
        The finding type this target wraps.
    """

    def __init__(self, rejig: Rejig, finding: F) -> None:
        super().__init__(rejig)
        self._finding = finding

    @property
    def finding(self) -> F:
        """The underlying finding."""
        return self._finding

    @property
    def file_path(self) -> Path:
        """Path to the file containing the finding."""
        return self._finding.file_path

    @property
    def line_number(self) -> int:
        """Line number of the finding."""
        return self._finding.line_number

    @property
    def name(self) -> str | None:
        """Name of the code element (if applicable)."""
        return self._finding.name

    @property
    def type(self) -> Enum:
        """Type of the finding."""
        return self._finding.type

    @property
    def message(self) -> str:
        """Description of the finding."""
        return self._finding.message

    @property
    def severity(self) -> str:
        """Severity level of the finding."""
        return self._finding.severity

    @property
    def location(self) -> str:
        """Formatted location string (file:line)."""
        return self._finding.location

    def exists(self) -> bool:
        """Check if the underlying file exists."""
        return self._finding.file_path.exists()

    def to_file_target(self) -> Target:
        """Navigate to the file containing this finding."""
        return self._rejig.file(self._finding.file_path)

    def to_line_target(self) -> Target:
        """Navigate to the line containing this finding."""
        return self._rejig.file(self._finding.file_path).line(self._finding.line_number)


class FindingTargetList(TargetList[FT], Generic[FT, E]):
    """Base class for finding-based target lists.

    Provides common filtering, aggregation, and sorting methods for target
    lists that contain findings (AnalysisTargetList, SecurityTargetList,
    OptimizeTargetList).

    Type Parameters
    ---------------
    FT : FindingTarget
        The target type in this list.
    E : Enum
        The enum type for finding types.

    Subclasses must implement:
    - _create_list: Factory method to create new instances of the subclass
    - _severity_order: Property returning severity ordering dict
    - _summary_prefix: Property returning the summary line prefix
    """

    def _create_list(self, targets: list[FT]) -> Self:
        """Create a new instance of this list type.

        Subclasses must override to return their specific type.
        """
        raise NotImplementedError("Subclasses must implement _create_list")

    @property
    def _severity_order(self) -> dict[str, int]:
        """Return severity ordering (lower = more severe).

        Subclasses should override with their severity scale.
        """
        return {"error": 0, "warning": 1, "info": 2}

    @property
    def _summary_prefix(self) -> str:
        """Return the prefix for summary output.

        Subclasses should override with their domain name.
        """
        return "findings"

    # ===== Type-based filtering =====

    def by_type(self, finding_type: E) -> Self:
        """Filter to findings of a specific type.

        Parameters
        ----------
        finding_type : E
            The type of findings to include.

        Returns
        -------
        Self
            Filtered list of findings.
        """
        return self._create_list([t for t in self._targets if t.type == finding_type])

    def by_types(self, *types: E) -> Self:
        """Filter to findings matching any of the given types.

        Parameters
        ----------
        *types : E
            Types of findings to include.

        Returns
        -------
        Self
            Filtered list of findings.
        """
        type_set = set(types)
        return self._create_list([t for t in self._targets if t.type in type_set])

    # ===== Severity filtering =====

    def by_severity(self, severity: str) -> Self:
        """Filter to findings with a specific severity.

        Parameters
        ----------
        severity : str
            Severity level to filter by.

        Returns
        -------
        Self
            Filtered list of findings.
        """
        return self._create_list([t for t in self._targets if t.severity == severity])

    # ===== Location filtering =====

    def in_file(self, path: Path | str) -> Self:
        """Filter to findings in a specific file.

        Parameters
        ----------
        path : Path | str
            Path to the file.

        Returns
        -------
        Self
            Filtered list of findings.
        """
        path = Path(path) if isinstance(path, str) else path
        return self._create_list([t for t in self._targets if t.file_path == path])

    def in_directory(self, directory: Path | str) -> Self:
        """Filter to findings in a specific directory (recursive).

        Parameters
        ----------
        directory : Path | str
            Path to the directory.

        Returns
        -------
        Self
            Filtered list of findings.
        """
        directory = Path(directory) if isinstance(directory, str) else directory
        return self._create_list(
            [
                t
                for t in self._targets
                if t.file_path == directory or directory in t.file_path.parents
            ]
        )

    # ===== Aggregation =====

    def group_by_file(self) -> dict[Path, Self]:
        """Group findings by file.

        Returns
        -------
        dict[Path, Self]
            Mapping of file paths to their findings.
        """
        groups: dict[Path, list[FT]] = {}
        for t in self._targets:
            if t.file_path not in groups:
                groups[t.file_path] = []
            groups[t.file_path].append(t)

        return {path: self._create_list(targets) for path, targets in groups.items()}

    def group_by_type(self) -> dict[E, Self]:
        """Group findings by type.

        Returns
        -------
        dict[E, Self]
            Mapping of types to their findings.
        """
        groups: dict[E, list[FT]] = {}
        for t in self._targets:
            if t.type not in groups:
                groups[t.type] = []
            groups[t.type].append(t)

        return {ftype: self._create_list(targets) for ftype, targets in groups.items()}

    def count_by_type(self) -> dict[E, int]:
        """Get counts by finding type.

        Returns
        -------
        dict[E, int]
            Mapping of types to counts.
        """
        counts: dict[E, int] = {}
        for t in self._targets:
            counts[t.type] = counts.get(t.type, 0) + 1
        return counts

    def count_by_severity(self) -> dict[str, int]:
        """Get counts by severity level.

        Returns
        -------
        dict[str, int]
            Mapping of severity levels to counts.
        """
        counts: dict[str, int] = {}
        for t in self._targets:
            counts[t.severity] = counts.get(t.severity, 0) + 1
        return counts

    def count_by_file(self) -> dict[Path, int]:
        """Get counts by file.

        Returns
        -------
        dict[Path, int]
            Mapping of file paths to finding counts.
        """
        counts: dict[Path, int] = {}
        for t in self._targets:
            counts[t.file_path] = counts.get(t.file_path, 0) + 1
        return counts

    # ===== Sorting =====

    def sorted_by_severity(self, descending: bool = True) -> Self:
        """Sort findings by severity.

        Parameters
        ----------
        descending : bool
            If True, most severe first. If False, least severe first.

        Returns
        -------
        Self
            Sorted list of findings.
        """
        sorted_targets = sorted(
            self._targets,
            key=lambda t: self._severity_order.get(t.severity, 99),
            reverse=not descending,
        )
        return self._create_list(sorted_targets)

    def sorted_by_location(self) -> Self:
        """Sort findings by file and line number.

        Returns
        -------
        Self
            Sorted list of findings.
        """
        sorted_targets = sorted(
            self._targets,
            key=lambda t: (str(t.file_path), t.line_number),
        )
        return self._create_list(sorted_targets)

    # ===== Output methods =====

    def to_list_of_dicts(self) -> list[dict]:
        """Convert to list of dictionaries for serialization.

        Returns base fields common to all finding types.
        Subclasses can override to add additional fields.

        Returns
        -------
        list[dict]
            List of finding dictionaries.
        """
        return [
            {
                "type": t.type.name,
                "file": str(t.file_path),
                "line": t.line_number,
                "name": t.name,
                "message": t.message,
                "severity": t.severity,
            }
            for t in self._targets
        ]

    def summary(self) -> str:
        """Generate a summary string of findings.

        Returns
        -------
        str
            Summary of findings by type.
        """
        counts = self.count_by_type()
        if not counts:
            return f"No {self._summary_prefix}"

        lines = [f"Total: {len(self._targets)} {self._summary_prefix}"]
        for ftype, count in sorted(counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {ftype.name}: {count}")
        return "\n".join(lines)
