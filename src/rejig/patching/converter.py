"""Converter for patches to rejig operations.

This module provides the PatchConverter class for converting patches
into rejig code and applying patches using rejig's target system.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import BatchResult, ErrorResult, Result
from rejig.patching.analyzer import DetectedOperation, OperationType, PatchAnalyzer
from rejig.patching.models import FilePatch, Hunk, Patch

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class PatchConverter:
    """Converter for patches to rejig operations.

    Provides three main capabilities:
    1. Generate rejig code strings from patches
    2. Generate complete executable Python scripts from patches
    3. Apply patches using rejig's target system

    Two modes are available:
    - smart_mode=True: Uses analyzer to detect operations and generate
      idiomatic rejig code (e.g., rename instead of rewrite)
    - smart_mode=False: Always uses line-based operations (more reliable)

    Examples
    --------
    >>> converter = PatchConverter(rj, smart_mode=True)
    >>> code = converter.to_rejig_code(patch)
    >>> print(code)
    rj.file("src/models.py").find_class("Foo").rename("Bar")

    >>> # Generate a complete script
    >>> script = converter.to_script(patch, description="Rename Foo to Bar")
    >>> Path("apply_patch.py").write_text(script)

    >>> # Apply directly
    >>> result = converter.apply(patch)
    """

    def __init__(
        self,
        rejig: Rejig,
        smart_mode: bool = True,
    ) -> None:
        """Initialize the converter.

        Parameters
        ----------
        rejig : Rejig
            The Rejig instance to use for operations.
        smart_mode : bool
            If True, use analyzer to detect high-level operations.
            If False, use line-based operations only.
        """
        self._rejig = rejig
        self._smart_mode = smart_mode
        self._analyzer = PatchAnalyzer() if smart_mode else None

    def to_rejig_code(
        self,
        patch: Patch,
        variable_name: str = "rj",
    ) -> str:
        """Convert a patch to rejig code.

        Parameters
        ----------
        patch : Patch
            The patch to convert.
        variable_name : str
            Variable name to use for the Rejig instance.

        Returns
        -------
        str
            Python code that would apply the same changes.
        """
        lines: list[str] = []

        if self._smart_mode and self._analyzer:
            operations = self._analyzer.get_optimal_operations(patch)
            for op in operations:
                code = self._operation_to_code(op, variable_name)
                if code:
                    lines.append(code)
        else:
            # Line-based mode
            for file_patch in patch.files:
                code = self._file_patch_to_code(file_patch, variable_name)
                lines.extend(code)

        return "\n".join(lines)

    def to_script(
        self,
        patch: Patch,
        variable_name: str = "rj",
        root_path: str = ".",
        description: str | None = None,
        dry_run: bool = False,
        include_error_handling: bool = True,
        include_summary: bool = True,
    ) -> str:
        """Generate a complete, executable Python script from a patch.

        Parameters
        ----------
        patch : Patch
            The patch to convert.
        variable_name : str
            Variable name for the Rejig instance.
        root_path : str
            Root path for the Rejig instance.
        description : str | None
            Optional description for the script docstring.
        dry_run : bool
            Whether to set dry_run=True on the Rejig instance.
        include_error_handling : bool
            Whether to include try/except and result checking.
        include_summary : bool
            Whether to include a summary of the patch as comments.

        Returns
        -------
        str
            A complete Python script that applies the patch changes.
        """
        lines: list[str] = []

        # Shebang
        lines.append("#!/usr/bin/env python3")

        # Module docstring
        if description:
            doc = description
        else:
            doc = f"Apply patch changes to {patch.file_count} file(s)"

        lines.append(f'"""')
        lines.append(doc)
        lines.append("")
        lines.append(f"Generated from patch: +{patch.total_additions}/-{patch.total_deletions} lines")
        lines.append(f'"""')
        lines.append("")

        # Imports
        lines.append("from pathlib import Path")
        lines.append("")
        lines.append("from rejig import Rejig")
        lines.append("")
        lines.append("")

        # Summary comments
        if include_summary:
            lines.append("# Patch Summary")
            lines.append(f"# Files: {patch.file_count}")
            lines.append(f"# Additions: +{patch.total_additions}")
            lines.append(f"# Deletions: -{patch.total_deletions}")
            lines.append("#")
            for fp in patch.files:
                status = ""
                if fp.is_new:
                    status = " (new)"
                elif fp.is_deleted:
                    status = " (deleted)"
                elif fp.is_renamed:
                    status = f" (renamed from {fp.old_path})"
                lines.append(f"#   {fp.path}{status}: +{fp.additions_count}/-{fp.deletions_count}")
            lines.append("")
            lines.append("")

        # Main function
        lines.append("def main() -> None:")
        lines.append(f'    """Apply the patch changes."""')

        # Rejig setup
        dry_run_str = ", dry_run=True" if dry_run else ""
        lines.append(f'    {variable_name} = Rejig("{root_path}"{dry_run_str})')
        lines.append("")

        # Generate operations
        operations_code = self.to_rejig_code(patch, variable_name)
        operation_lines = operations_code.splitlines()

        if include_error_handling:
            lines.append("    # Apply changes")
            lines.append("    results = []")
            lines.append("")

            for op_line in operation_lines:
                op_line = op_line.strip()
                if not op_line:
                    continue
                if op_line.startswith("#"):
                    # It's a comment
                    lines.append(f"    {op_line}")
                else:
                    # It's an operation - wrap with result capture
                    lines.append(f"    result = {op_line}")
                    lines.append("    results.append(result)")
                    lines.append("    if not result.success:")
                    lines.append(f'        print(f"Warning: {{result.message}}")')
                    lines.append("")

            lines.append("    # Report results")
            lines.append("    success_count = sum(1 for r in results if r.success)")
            lines.append("    total_count = len(results)")
            lines.append('    print(f"Completed: {success_count}/{total_count} operations succeeded")')
            lines.append("")
            lines.append("    if success_count < total_count:")
            lines.append("        failed = [r for r in results if not r.success]")
            lines.append("        for r in failed:")
            lines.append('            print(f"  Failed: {r.message}")')
        else:
            # Simple mode without error handling
            for op_line in operation_lines:
                op_line = op_line.strip()
                if not op_line:
                    continue
                lines.append(f"    {op_line}")

        lines.append("")
        lines.append("")

        # Main block
        lines.append('if __name__ == "__main__":')
        lines.append("    main()")
        lines.append("")

        return "\n".join(lines)

    def save_script(
        self,
        patch: Patch,
        path: Path | str,
        overwrite: bool = False,
        **kwargs,
    ) -> Result:
        """Generate and save a Python script from a patch.

        Parameters
        ----------
        patch : Patch
            The patch to convert.
        path : Path | str
            Output file path.
        overwrite : bool
            Whether to overwrite existing file.
        **kwargs
            Additional arguments passed to to_script().

        Returns
        -------
        Result
            Result indicating success or failure.
        """
        path = Path(path) if isinstance(path, str) else path

        if path.exists() and not overwrite:
            return ErrorResult(
                message=f"File already exists: {path}",
                operation="save_script",
            )

        try:
            script = self.to_script(patch, **kwargs)
            path.write_text(script)
            # Make executable
            path.chmod(path.stat().st_mode | 0o111)
            return Result(
                success=True,
                message=f"Saved script to {path}",
                files_changed=[path],
            )
        except Exception as e:
            return ErrorResult(
                message=f"Failed to save script: {e}",
                operation="save_script",
                exception=e,
            )

    def apply(self, patch: Patch) -> Result:
        """Apply a patch using rejig operations.

        Parameters
        ----------
        patch : Patch
            The patch to apply.

        Returns
        -------
        Result
            Result of applying the patch.
        """
        results: list[Result] = []

        for file_patch in patch.files:
            result = self._apply_file_patch(file_patch)
            results.append(result)

        if not results:
            return Result(success=True, message="No changes to apply")

        # Aggregate results
        all_succeeded = all(r.success for r in results)
        files_changed = []
        diffs: dict[Path, str] = {}

        for r in results:
            files_changed.extend(r.files_changed)
            diffs.update(r.diffs)

        if all_succeeded:
            return Result(
                success=True,
                message=f"Applied patch to {len(files_changed)} file(s)",
                files_changed=files_changed,
                diffs=diffs,
            )
        else:
            failed = [r for r in results if not r.success]
            return ErrorResult(
                message=f"Patch application had {len(failed)} failure(s)",
                operation="apply_patch",
            )

    def _operation_to_code(
        self,
        op: DetectedOperation,
        var: str,
    ) -> str | None:
        """Convert a detected operation to rejig code."""
        path_str = str(op.file_path)

        if op.type == OperationType.CLASS_RENAME:
            old = op.details["old_name"]
            new = op.details["new_name"]
            return f'{var}.file("{path_str}").find_class("{old}").rename("{new}")'

        elif op.type == OperationType.FUNCTION_RENAME:
            old = op.details["old_name"]
            new = op.details["new_name"]
            return f'{var}.file("{path_str}").find_function("{old}").rename("{new}")'

        elif op.type == OperationType.METHOD_RENAME:
            old = op.details["old_name"]
            new = op.details["new_name"]
            cls = op.details.get("class")
            if cls:
                return f'{var}.file("{path_str}").find_class("{cls}").find_method("{old}").rename("{new}")'
            else:
                # Without class context, use find_method on file
                return f'# Method rename: {old} -> {new} (class context unknown)'

        elif op.type == OperationType.CLASS_ADD:
            name = op.details["name"]
            return f'# Class add: {name} (use add_class with body)'

        elif op.type == OperationType.CLASS_DELETE:
            name = op.details["name"]
            return f'{var}.file("{path_str}").find_class("{name}").delete()'

        elif op.type == OperationType.FUNCTION_ADD:
            name = op.details["name"]
            return f'# Function add: {name} (use add_function with body)'

        elif op.type == OperationType.FUNCTION_DELETE:
            name = op.details["name"]
            return f'{var}.file("{path_str}").find_function("{name}").delete()'

        elif op.type == OperationType.METHOD_ADD:
            name = op.details["name"]
            cls = op.details.get("class")
            if cls:
                return f'# Method add: {cls}.{name} (use add_method with body)'
            return f'# Method add: {name} (class context unknown)'

        elif op.type == OperationType.METHOD_DELETE:
            name = op.details["name"]
            cls = op.details.get("class")
            if cls:
                return f'{var}.file("{path_str}").find_class("{cls}").find_method("{name}").delete()'
            return f'# Method delete: {name} (class context unknown)'

        elif op.type == OperationType.DECORATOR_ADD:
            dec = op.details["decorator"]
            return f'# Decorator add: @{dec} (use add_decorator)'

        elif op.type == OperationType.DECORATOR_REMOVE:
            dec = op.details["decorator"]
            return f'# Decorator remove: @{dec} (use remove_decorator)'

        elif op.type == OperationType.IMPORT_ADD:
            imp = op.details["import"]
            return f'{var}.file("{path_str}").add_import("{imp}")'

        elif op.type == OperationType.IMPORT_REMOVE:
            imp = op.details["import"]
            return f'# Import remove: {imp} (use remove_import)'

        elif op.type == OperationType.LINE_REWRITE:
            start = op.details["start_line"]
            end = op.details["end_line"]
            new_content = op.details["new_content"]
            # Escape the content for code
            escaped = new_content.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            return f'{var}.file("{path_str}").lines({start}, {end}).rewrite("{escaped}")'

        elif op.type == OperationType.LINE_INSERT:
            at_line = op.details["at_line"]
            content = op.details["content"]
            escaped = content.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            return f'{var}.file("{path_str}").line({at_line}).insert_before("{escaped}")'

        elif op.type == OperationType.LINE_DELETE:
            start = op.details["start_line"]
            end = op.details["end_line"]
            return f'{var}.file("{path_str}").lines({start}, {end}).delete()'

        elif op.type == OperationType.FILE_CREATE:
            path = op.details["path"]
            return f'# File create: {path} (use write_file)'

        elif op.type == OperationType.FILE_DELETE:
            path = op.details["path"]
            return f'# File delete: {path} (use delete_file)'

        elif op.type == OperationType.FILE_RENAME:
            old = op.details["old_path"]
            new = op.details["new_path"]
            return f'# File rename: {old} -> {new} (use rename_file)'

        return None

    def _file_patch_to_code(
        self,
        file_patch: FilePatch,
        var: str,
    ) -> list[str]:
        """Convert a file patch to line-based rejig code."""
        lines: list[str] = []
        path_str = str(file_patch.path)

        if file_patch.is_new:
            lines.append(f'# New file: {path_str}')
            # Would need to generate full file content
            return lines

        if file_patch.is_deleted:
            lines.append(f'# Deleted file: {file_patch.old_path}')
            return lines

        if file_patch.is_renamed:
            lines.append(f'# Renamed: {file_patch.old_path} -> {file_patch.new_path}')

        for i, hunk in enumerate(file_patch.hunks):
            hunk_code = self._hunk_to_code(hunk, path_str, var)
            lines.extend(hunk_code)

        return lines

    def _hunk_to_code(
        self,
        hunk: Hunk,
        path_str: str,
        var: str,
    ) -> list[str]:
        """Convert a hunk to line-based rejig code."""
        # Determine the operation type from the hunk
        has_deletions = bool(hunk.deletions)
        has_additions = bool(hunk.additions)

        if has_deletions and has_additions:
            # This is a rewrite
            new_content = hunk.get_new_content()
            escaped = new_content.replace("\\", "\\\\").replace('"', '\\"')
            # Use multiline string for readability
            if "\n" in new_content:
                return [
                    f'{var}.file("{path_str}").lines({hunk.old_start}, {hunk.old_start + hunk.old_count - 1}).rewrite(',
                    f'    """{new_content}"""',
                    ')',
                ]
            else:
                return [
                    f'{var}.file("{path_str}").lines({hunk.old_start}, {hunk.old_start + hunk.old_count - 1}).rewrite("{escaped}")'
                ]

        elif has_additions:
            # This is an insertion
            new_content = hunk.get_new_content()
            escaped = new_content.replace("\\", "\\\\").replace('"', '\\"')
            if "\n" in new_content:
                return [
                    f'{var}.file("{path_str}").line({hunk.new_start}).insert_before(',
                    f'    """{new_content}"""',
                    ')',
                ]
            else:
                return [
                    f'{var}.file("{path_str}").line({hunk.new_start}).insert_before("{escaped}")'
                ]

        elif has_deletions:
            # This is a deletion
            return [
                f'{var}.file("{path_str}").lines({hunk.old_start}, {hunk.old_start + hunk.old_count - 1}).delete()'
            ]

        return []

    def _apply_file_patch(self, file_patch: FilePatch) -> Result:
        """Apply a single file patch using rejig operations."""
        path = file_patch.path

        if file_patch.is_new:
            # Create new file
            return self._apply_new_file(file_patch)

        if file_patch.is_deleted:
            # Delete file
            old_path = file_patch.old_path
            if old_path and old_path.exists():
                try:
                    old_path.unlink()
                    return Result(
                        success=True,
                        message=f"Deleted {old_path}",
                        files_changed=[old_path],
                    )
                except Exception as e:
                    return ErrorResult(
                        message=f"Failed to delete {old_path}: {e}",
                        operation="delete_file",
                        exception=e,
                    )
            return Result(success=True, message="File already deleted")

        if not path:
            return ErrorResult(
                message="No path for file patch",
                operation="apply_file_patch",
            )

        # Read current file content
        resolved_path = self._rejig._resolve_path(path)
        if not resolved_path.exists():
            return ErrorResult(
                message=f"File does not exist: {resolved_path}",
                operation="apply_file_patch",
            )

        try:
            content = resolved_path.read_text()
        except Exception as e:
            return ErrorResult(
                message=f"Failed to read {resolved_path}: {e}",
                operation="apply_file_patch",
                exception=e,
            )

        # Apply hunks in reverse order to preserve line numbers
        hunks_reversed = list(reversed(file_patch.hunks))
        new_content = content

        for hunk in hunks_reversed:
            new_content = self._apply_hunk(new_content, hunk)

        # Write the modified content
        target = self._rejig.file(resolved_path)
        return target.rewrite(new_content)

    def _apply_new_file(self, file_patch: FilePatch) -> Result:
        """Apply a new file patch."""
        path = file_patch.new_path
        if not path:
            return ErrorResult(
                message="No path for new file",
                operation="apply_new_file",
            )

        # Reconstruct content from hunks
        lines: list[str] = []
        for hunk in file_patch.hunks:
            for change in hunk.changes:
                if change.is_addition or change.is_context:
                    lines.append(change.content)

        content = "\n".join(lines)
        if content and not content.endswith("\n"):
            content += "\n"

        resolved = self._rejig._resolve_path(path)
        if resolved.exists() and not self._rejig.dry_run:
            return ErrorResult(
                message=f"File already exists: {resolved}",
                operation="apply_new_file",
            )

        if self._rejig.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would create {resolved}",
                files_changed=[resolved],
            )

        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content)
            return Result(
                success=True,
                message=f"Created {resolved}",
                files_changed=[resolved],
            )
        except Exception as e:
            return ErrorResult(
                message=f"Failed to create {resolved}: {e}",
                operation="apply_new_file",
                exception=e,
            )

    def _apply_hunk(self, content: str, hunk: Hunk) -> str:
        """Apply a single hunk to content.

        Replaces lines from old_start to old_start+old_count with
        the new content from additions.
        """
        lines = content.splitlines(keepends=True)

        # Convert to 0-based indexing
        start_idx = hunk.old_start - 1
        end_idx = start_idx + hunk.old_count

        # Build new lines from the hunk
        new_lines: list[str] = []
        for change in hunk.changes:
            if change.is_addition or change.is_context:
                line = change.content
                if not line.endswith("\n"):
                    line += "\n"
                new_lines.append(line)

        # Replace the range
        result_lines = lines[:start_idx] + new_lines + lines[end_idx:]
        return "".join(result_lines)


def convert_patch_to_code(
    patch: Patch,
    rejig: Rejig,
    smart_mode: bool = True,
    variable_name: str = "rj",
) -> str:
    """Convenience function to convert a patch to rejig code.

    Parameters
    ----------
    patch : Patch
        The patch to convert.
    rejig : Rejig
        The Rejig instance (used for path resolution).
    smart_mode : bool
        Whether to use smart detection of operations.
    variable_name : str
        Variable name for the Rejig instance.

    Returns
    -------
    str
        Python code that would apply the changes.
    """
    converter = PatchConverter(rejig, smart_mode)
    return converter.to_rejig_code(patch, variable_name)


def apply_patch(patch: Patch, rejig: Rejig) -> Result:
    """Convenience function to apply a patch.

    Parameters
    ----------
    patch : Patch
        The patch to apply.
    rejig : Rejig
        The Rejig instance.

    Returns
    -------
    Result
        Result of applying the patch.
    """
    converter = PatchConverter(rejig)
    return converter.apply(patch)


def generate_script_from_patch(
    patch: Patch,
    rejig: Rejig,
    smart_mode: bool = True,
    **kwargs,
) -> str:
    """Convenience function to generate a Python script from a patch.

    Parameters
    ----------
    patch : Patch
        The patch to convert.
    rejig : Rejig
        The Rejig instance (used for path resolution).
    smart_mode : bool
        Whether to use smart detection of operations.
    **kwargs
        Additional arguments passed to to_script():
        - variable_name: str = "rj"
        - root_path: str = "."
        - description: str | None = None
        - dry_run: bool = False
        - include_error_handling: bool = True
        - include_summary: bool = True

    Returns
    -------
    str
        A complete Python script.
    """
    converter = PatchConverter(rejig, smart_mode)
    return converter.to_script(patch, **kwargs)


def save_script_from_patch(
    patch: Patch,
    rejig: Rejig,
    path: Path | str,
    smart_mode: bool = True,
    overwrite: bool = False,
    **kwargs,
) -> Result:
    """Convenience function to generate and save a Python script from a patch.

    Parameters
    ----------
    patch : Patch
        The patch to convert.
    rejig : Rejig
        The Rejig instance.
    path : Path | str
        Output file path.
    smart_mode : bool
        Whether to use smart detection of operations.
    overwrite : bool
        Whether to overwrite existing file.
    **kwargs
        Additional arguments passed to to_script().

    Returns
    -------
    Result
        Result indicating success or failure.
    """
    converter = PatchConverter(rejig, smart_mode)
    return converter.save_script(patch, path, overwrite, **kwargs)
