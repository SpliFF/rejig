"""ModuleTarget for operations on Python modules by dotted path."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rejig.targets.base import ErrorTarget, Result, Target, TargetList
from rejig.targets.python.file import FileTarget

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class ModuleTarget(Target):
    """Target for a Python module identified by dotted path.

    This target resolves a dotted module path (e.g., 'myapp.models.user')
    to the corresponding Python file and provides operations on it.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    module_path : str
        Dotted module path (e.g., "myapp.models" or "myapp.models.user").

    Examples
    --------
    >>> module = rj.module("myapp.models")
    >>> module.find_class("User").add_attribute("email", "str")
    >>> module.add_import("from typing import Optional")
    """

    def __init__(self, rejig: Rejig, module_path: str) -> None:
        super().__init__(rejig)
        self.module_path = module_path
        self._resolved_path: Path | None = None
        self._file_target: FileTarget | None = None

    @property
    def file_path(self) -> Path | None:
        """Resolved filesystem path for this module."""
        if self._resolved_path is None:
            self._resolve_path()
        return self._resolved_path

    def __repr__(self) -> str:
        if self._resolved_path:
            return f"ModuleTarget({self.module_path!r}, path={self._resolved_path})"
        return f"ModuleTarget({self.module_path!r})"

    def _resolve_path(self) -> Path | None:
        """Resolve the module path to a filesystem path."""
        if self._resolved_path is not None:
            return self._resolved_path

        # Convert dotted path to filesystem path components
        parts = self.module_path.split(".")

        # Try to find matching file in the project
        for file_path in self._rejig.files:
            # Check if this file matches the module path
            # e.g., "myapp/models/user.py" should match "myapp.models.user"

            # Get relative path from project root
            try:
                rel_path = file_path.relative_to(self._rejig.root)
            except ValueError:
                continue

            # Convert path to module-style dotted path
            path_parts = list(rel_path.parts)
            if path_parts[-1].endswith(".py"):
                path_parts[-1] = path_parts[-1][:-3]  # Remove .py

            # Handle __init__.py as package
            if path_parts[-1] == "__init__":
                path_parts = path_parts[:-1]

            # Check if this matches our module path
            if path_parts == parts:
                self._resolved_path = file_path
                return file_path

            # Also check if it's a package (directory with __init__.py)
            if path_parts[:-1] == parts and path_parts[-1] == "__init__":
                self._resolved_path = file_path
                return file_path

        return None

    def _get_file_target(self) -> FileTarget | None:
        """Get the underlying FileTarget for this module."""
        if self._file_target is not None:
            return self._file_target

        file_path = self._resolve_path()
        if file_path:
            self._file_target = FileTarget(self._rejig, file_path)
            return self._file_target
        return None

    def exists(self) -> bool:
        """Check if this module exists."""
        return self._resolve_path() is not None

    def get_content(self) -> Result:
        """Get the content of this module's file.

        Returns
        -------
        Result
            Result with file content in `data` field if successful.
        """
        file_target = self._get_file_target()
        if not file_target:
            return self._operation_failed(
                "get_content", f"Module '{self.module_path}' not found"
            )
        return file_target.get_content()

    # ===== Navigation methods - delegate to FileTarget =====

    def find_class(self, name: str) -> Target:
        """Find a class by name in this module.

        Parameters
        ----------
        name : str
            Name of the class to find.

        Returns
        -------
        ClassTarget | ErrorTarget
            ClassTarget if found, ErrorTarget otherwise.
        """
        file_target = self._get_file_target()
        if not file_target:
            return ErrorTarget(self._rejig, f"Module '{self.module_path}' not found")
        return file_target.find_class(name)

    def find_function(self, name: str) -> Target:
        """Find a module-level function by name in this module.

        Parameters
        ----------
        name : str
            Name of the function to find.

        Returns
        -------
        FunctionTarget | ErrorTarget
            FunctionTarget if found, ErrorTarget otherwise.
        """
        file_target = self._get_file_target()
        if not file_target:
            return ErrorTarget(self._rejig, f"Module '{self.module_path}' not found")
        return file_target.find_function(name)

    def find_classes(self, pattern: str | None = None) -> TargetList[Target]:
        """Find all classes in this module.

        Parameters
        ----------
        pattern : str | None
            Optional regex pattern to filter class names.

        Returns
        -------
        TargetList[ClassTarget]
            List of matching ClassTarget objects.
        """
        file_target = self._get_file_target()
        if not file_target:
            return TargetList(self._rejig, [])
        return file_target.find_classes(pattern)

    def find_functions(self, pattern: str | None = None) -> TargetList[Target]:
        """Find all module-level functions in this module.

        Parameters
        ----------
        pattern : str | None
            Optional regex pattern to filter function names.

        Returns
        -------
        TargetList[FunctionTarget]
            List of matching FunctionTarget objects.
        """
        file_target = self._get_file_target()
        if not file_target:
            return TargetList(self._rejig, [])
        return file_target.find_functions(pattern)

    def line(self, line_number: int) -> Target:
        """Get a specific line of this module.

        Parameters
        ----------
        line_number : int
            1-based line number.

        Returns
        -------
        LineTarget
            Target for the specified line.
        """
        file_target = self._get_file_target()
        if not file_target:
            return ErrorTarget(self._rejig, f"Module '{self.module_path}' not found")
        return file_target.line(line_number)

    def lines(self, start: int, end: int) -> Target:
        """Get a range of lines from this module.

        Parameters
        ----------
        start : int
            1-based starting line number.
        end : int
            1-based ending line number (inclusive).

        Returns
        -------
        LineBlockTarget
            Target for the specified line range.
        """
        file_target = self._get_file_target()
        if not file_target:
            return ErrorTarget(self._rejig, f"Module '{self.module_path}' not found")
        return file_target.lines(start, end)

    # ===== Modification operations - delegate to FileTarget =====

    def add_import(self, import_statement: str) -> Result:
        """Add an import statement to this module.

        Parameters
        ----------
        import_statement : str
            Import statement to add (without newline).

        Returns
        -------
        Result
            Result of the operation.
        """
        file_target = self._get_file_target()
        if not file_target:
            return self._operation_failed(
                "add_import", f"Module '{self.module_path}' not found"
            )
        return file_target.add_import(import_statement)

    def add_class(self, name: str, body: str = "pass", **kwargs: str) -> Result:
        """Add a class to this module.

        Parameters
        ----------
        name : str
            Name of the class to add.
        body : str
            Body of the class (default: "pass").
        **kwargs
            Additional options (bases, decorators).

        Returns
        -------
        Result
            Result of the operation.
        """
        file_target = self._get_file_target()
        if not file_target:
            return self._operation_failed(
                "add_class", f"Module '{self.module_path}' not found"
            )
        return file_target.add_class(name, body, **kwargs)

    def add_function(self, name: str, body: str = "pass", **kwargs: str) -> Result:
        """Add a module-level function to this module.

        Parameters
        ----------
        name : str
            Name of the function to add.
        body : str
            Body of the function (default: "pass").
        **kwargs
            Additional options (params, return_type, decorators).

        Returns
        -------
        Result
            Result of the operation.
        """
        file_target = self._get_file_target()
        if not file_target:
            return self._operation_failed(
                "add_function", f"Module '{self.module_path}' not found"
            )
        return file_target.add_function(name, body, **kwargs)

    def rewrite(self, new_content: str) -> Result:
        """Replace the entire content of this module.

        Parameters
        ----------
        new_content : str
            New content for the module.

        Returns
        -------
        Result
            Result of the operation.
        """
        file_target = self._get_file_target()
        if not file_target:
            return self._operation_failed(
                "rewrite", f"Module '{self.module_path}' not found"
            )
        return file_target.rewrite(new_content)

    def delete(self) -> Result:
        """Delete this module's file.

        Returns
        -------
        Result
            Result of the operation.
        """
        file_target = self._get_file_target()
        if not file_target:
            return self._operation_failed(
                "delete", f"Module '{self.module_path}' not found"
            )
        return file_target.delete()
