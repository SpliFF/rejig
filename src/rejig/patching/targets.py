"""Target classes for patch manipulation.

This module provides Target classes that integrate patches with
rejig's fluent API, allowing patches to be manipulated using the
standard target patterns.

Classes:
- PatchTarget - Main target for a complete patch
- PatchFileTarget - Target for a single file within a patch
- PatchHunkTarget - Target for a single hunk within a file patch
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from rejig.core.results import ErrorResult, Result
from rejig.patching.analyzer import DetectedOperation, PatchAnalyzer
from rejig.patching.converter import PatchConverter
from rejig.patching.models import FilePatch, Hunk, Patch
from rejig.targets.base import Target, TargetList

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class PatchTarget(Target):
    """Target for a complete patch.

    Provides a fluent API for working with patches, including
    applying, reversing, and converting to rejig code.

    Examples
    --------
    >>> patch = rj.patch_from_file("changes.patch")
    >>> print(patch.file_count)
    >>> print(patch.total_additions)
    >>> result = patch.apply()

    >>> # Reverse a patch
    >>> undo = patch.reverse()
    >>> undo.apply()

    >>> # Generate rejig code
    >>> code = patch.to_rejig_code()

    >>> # Generate a complete Python script
    >>> script = patch.to_script(description="Apply refactoring")
    >>> patch.save_script("apply_changes.py")
    """

    def __init__(self, rejig: Rejig, patch: Patch) -> None:
        """Initialize the patch target.

        Parameters
        ----------
        rejig : Rejig
            The parent Rejig instance.
        patch : Patch
            The Patch object to wrap.
        """
        super().__init__(rejig)
        self._patch = patch
        self._converter = PatchConverter(rejig)
        self._analyzer = PatchAnalyzer()

    @property
    def patch(self) -> Patch:
        """The underlying Patch object."""
        return self._patch

    def exists(self) -> bool:
        """Check if the patch has any files."""
        return bool(self._patch.files)

    # ===== Properties from Patch =====

    @property
    def file_count(self) -> int:
        """Number of files in the patch."""
        return self._patch.file_count

    @property
    def total_additions(self) -> int:
        """Total added lines across all files."""
        return self._patch.total_additions

    @property
    def total_deletions(self) -> int:
        """Total deleted lines across all files."""
        return self._patch.total_deletions

    @property
    def paths(self) -> list[Path]:
        """All file paths affected by this patch."""
        return self._patch.paths

    # ===== Navigation methods =====

    def files(self) -> TargetList[PatchFileTarget]:
        """Get all file targets in this patch.

        Returns
        -------
        TargetList[PatchFileTarget]
            List of file targets.
        """
        targets = [
            PatchFileTarget(self._rejig, fp, self)
            for fp in self._patch.files
        ]
        return TargetList(self._rejig, targets)

    def file(self, path: Path | str) -> PatchFileTarget | None:
        """Get a specific file target by path.

        Parameters
        ----------
        path : Path | str
            Path to look up.

        Returns
        -------
        PatchFileTarget | None
            The file target, or None if not found.
        """
        path = Path(path) if isinstance(path, str) else path
        fp = self._patch.get_file(path)
        if fp:
            return PatchFileTarget(self._rejig, fp, self)
        return None

    # ===== Operations =====

    def apply(self) -> Result:
        """Apply the patch using rejig operations.

        Returns
        -------
        Result
            Result of applying the patch.
        """
        return self._converter.apply(self._patch)

    def reverse(self) -> PatchTarget:
        """Create a reversed patch target (undo).

        Returns
        -------
        PatchTarget
            A new PatchTarget that reverses all changes.
        """
        reversed_patch = self._patch.reverse()
        return PatchTarget(self._rejig, reversed_patch)

    def to_rejig_code(
        self,
        variable_name: str = "rj",
        smart_mode: bool = True,
    ) -> str:
        """Convert the patch to rejig Python code.

        Parameters
        ----------
        variable_name : str
            Variable name for the Rejig instance.
        smart_mode : bool
            If True, detect high-level operations.
            If False, use line-based operations only.

        Returns
        -------
        str
            Python code that would apply the same changes.
        """
        converter = PatchConverter(self._rejig, smart_mode)
        return converter.to_rejig_code(self._patch, variable_name)

    def to_script(
        self,
        variable_name: str = "rj",
        root_path: str = ".",
        description: str | None = None,
        dry_run: bool = False,
        smart_mode: bool = True,
        include_error_handling: bool = True,
        include_summary: bool = True,
    ) -> str:
        """Generate a complete, executable Python script from this patch.

        Creates a standalone Python script that uses rejig operations
        to apply the same changes as the patch.

        Parameters
        ----------
        variable_name : str
            Variable name for the Rejig instance in the script.
        root_path : str
            Root path for the Rejig instance in the script.
        description : str | None
            Optional description for the script docstring.
        dry_run : bool
            Whether to set dry_run=True on the Rejig instance.
        smart_mode : bool
            If True, detect high-level operations.
            If False, use line-based operations only.
        include_error_handling : bool
            Whether to include try/except and result checking.
        include_summary : bool
            Whether to include a summary of the patch as comments.

        Returns
        -------
        str
            A complete Python script that applies the patch changes.

        Examples
        --------
        >>> patch = rj.patch_from_file("changes.patch")
        >>> script = patch.to_script(description="Apply bugfix")
        >>> Path("apply_bugfix.py").write_text(script)
        """
        converter = PatchConverter(self._rejig, smart_mode)
        return converter.to_script(
            self._patch,
            variable_name=variable_name,
            root_path=root_path,
            description=description,
            dry_run=dry_run,
            include_error_handling=include_error_handling,
            include_summary=include_summary,
        )

    def save_script(
        self,
        path: Path | str,
        overwrite: bool = False,
        **kwargs,
    ) -> Result:
        """Generate and save a Python script from this patch.

        Creates a standalone, executable Python script that uses rejig
        operations to apply the same changes as the patch.

        Parameters
        ----------
        path : Path | str
            Output file path.
        overwrite : bool
            Whether to overwrite existing file.
        **kwargs
            Additional arguments passed to to_script():
            - variable_name: str = "rj"
            - root_path: str = "."
            - description: str | None = None
            - dry_run: bool = False
            - smart_mode: bool = True
            - include_error_handling: bool = True
            - include_summary: bool = True

        Returns
        -------
        Result
            Result indicating success or failure.

        Examples
        --------
        >>> patch = rj.patch_from_file("changes.patch")
        >>> result = patch.save_script("apply_changes.py")
        >>> if result.success:
        ...     print(f"Script saved to {result.files_changed[0]}")
        """
        path = Path(path) if isinstance(path, str) else path

        if path.exists() and not overwrite:
            return ErrorResult(
                message=f"File already exists: {path}",
                operation="save_script",
            )

        try:
            script = self.to_script(**kwargs)
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

    def to_unified_diff(self) -> str:
        """Convert to unified diff format.

        Returns
        -------
        str
            The patch as a unified diff string.
        """
        return self._patch.to_unified_diff()

    def save(self, path: Path | str, overwrite: bool = False) -> Result:
        """Save the patch to a file.

        Parameters
        ----------
        path : Path | str
            Output file path.
        overwrite : bool
            Whether to overwrite existing file.

        Returns
        -------
        Result
            Result indicating success or failure.
        """
        path = Path(path) if isinstance(path, str) else path

        if path.exists() and not overwrite:
            return ErrorResult(
                message=f"File already exists: {path}",
                operation="save",
            )

        try:
            diff_text = self._patch.to_unified_diff()
            path.write_text(diff_text)
            return Result(
                success=True,
                message=f"Saved patch to {path}",
                files_changed=[path],
            )
        except Exception as e:
            return ErrorResult(
                message=f"Failed to save patch: {e}",
                operation="save",
                exception=e,
            )

    def analyze(self) -> list[DetectedOperation]:
        """Analyze the patch to detect operations.

        Returns
        -------
        list[DetectedOperation]
            List of detected operations.
        """
        return self._analyzer.analyze(self._patch)

    def summary(self) -> str:
        """Get a human-readable summary of the patch.

        Returns
        -------
        str
            Summary string.
        """
        return self._patch.summary()

    def get_content(self) -> Result:
        """Get the patch content as unified diff.

        Returns
        -------
        Result
            Result with diff content in data field.
        """
        return Result(
            success=True,
            message=f"Patch with {self.file_count} file(s)",
            data=self._patch.to_unified_diff(),
        )

    def __repr__(self) -> str:
        return f"PatchTarget({self.file_count} files, +{self.total_additions}/-{self.total_deletions})"

    def __iter__(self) -> Iterator[PatchFileTarget]:
        """Iterate over file targets."""
        for fp in self._patch.files:
            yield PatchFileTarget(self._rejig, fp, self)


class PatchFileTarget(Target):
    """Target for a single file within a patch.

    Provides access to hunks and file-level operations.

    Examples
    --------
    >>> patch = rj.patch_from_file("changes.patch")
    >>> for file_target in patch.files():
    ...     print(f"{file_target.path}: +{file_target.additions_count}")
    """

    def __init__(
        self,
        rejig: Rejig,
        file_patch: FilePatch,
        parent: PatchTarget,
    ) -> None:
        """Initialize the file target.

        Parameters
        ----------
        rejig : Rejig
            The parent Rejig instance.
        file_patch : FilePatch
            The FilePatch object to wrap.
        parent : PatchTarget
            The parent patch target.
        """
        super().__init__(rejig)
        self._file_patch = file_patch
        self._parent = parent

    @property
    def file_patch(self) -> FilePatch:
        """The underlying FilePatch object."""
        return self._file_patch

    def exists(self) -> bool:
        """Check if the file patch has changes."""
        return self._file_patch.has_changes

    @property
    def path(self) -> Path | None:
        """Primary path for this file."""
        return self._file_patch.path

    @property
    def old_path(self) -> Path | None:
        """Original path (for renames)."""
        return self._file_patch.old_path

    @property
    def new_path(self) -> Path | None:
        """New path (for renames and new files)."""
        return self._file_patch.new_path

    @property
    def is_new(self) -> bool:
        """Whether this is a new file."""
        return self._file_patch.is_new

    @property
    def is_deleted(self) -> bool:
        """Whether this file is deleted."""
        return self._file_patch.is_deleted

    @property
    def is_renamed(self) -> bool:
        """Whether this file is renamed."""
        return self._file_patch.is_renamed

    @property
    def additions_count(self) -> int:
        """Total added lines."""
        return self._file_patch.additions_count

    @property
    def deletions_count(self) -> int:
        """Total deleted lines."""
        return self._file_patch.deletions_count

    @property
    def hunk_count(self) -> int:
        """Number of hunks."""
        return len(self._file_patch.hunks)

    # ===== Navigation =====

    def hunks(self) -> TargetList[PatchHunkTarget]:
        """Get all hunk targets.

        Returns
        -------
        TargetList[PatchHunkTarget]
            List of hunk targets.
        """
        targets = [
            PatchHunkTarget(self._rejig, h, i, self)
            for i, h in enumerate(self._file_patch.hunks)
        ]
        return TargetList(self._rejig, targets)

    def hunk(self, index: int) -> PatchHunkTarget | None:
        """Get a specific hunk by index.

        Parameters
        ----------
        index : int
            Zero-based hunk index.

        Returns
        -------
        PatchHunkTarget | None
            The hunk target, or None if index out of range.
        """
        if 0 <= index < len(self._file_patch.hunks):
            return PatchHunkTarget(
                self._rejig,
                self._file_patch.hunks[index],
                index,
                self,
            )
        return None

    # ===== Operations =====

    def apply(self) -> Result:
        """Apply this file's changes.

        Returns
        -------
        Result
            Result of applying the changes.
        """
        converter = PatchConverter(self._rejig)
        return converter._apply_file_patch(self._file_patch)

    def reverse(self) -> PatchFileTarget:
        """Create a reversed file target.

        Returns
        -------
        PatchFileTarget
            A new target that reverses the changes.
        """
        reversed_fp = self._file_patch.reverse()
        return PatchFileTarget(self._rejig, reversed_fp, self._parent)

    def to_unified_diff(self) -> str:
        """Convert to unified diff format.

        Returns
        -------
        str
            The file patch as unified diff.
        """
        return self._file_patch.to_unified_diff()

    def get_content(self) -> Result:
        """Get the diff content for this file.

        Returns
        -------
        Result
            Result with diff in data field.
        """
        return Result(
            success=True,
            message=f"File patch for {self.path}",
            data=self._file_patch.to_unified_diff(),
        )

    def __repr__(self) -> str:
        status = ""
        if self.is_new:
            status = " (new)"
        elif self.is_deleted:
            status = " (deleted)"
        elif self.is_renamed:
            status = " (renamed)"
        return f"PatchFileTarget({self.path}{status}, {self.hunk_count} hunks)"

    def __iter__(self) -> Iterator[PatchHunkTarget]:
        """Iterate over hunk targets."""
        for i, h in enumerate(self._file_patch.hunks):
            yield PatchHunkTarget(self._rejig, h, i, self)


class PatchHunkTarget(Target):
    """Target for a single hunk within a file patch.

    Provides access to individual changes within a hunk.

    Examples
    --------
    >>> patch = rj.patch_from_file("changes.patch")
    >>> file_target = patch.file("src/models.py")
    >>> for hunk in file_target.hunks():
    ...     print(f"@@ {hunk.old_start} -> {hunk.new_start}")
    """

    def __init__(
        self,
        rejig: Rejig,
        hunk: Hunk,
        index: int,
        parent: PatchFileTarget,
    ) -> None:
        """Initialize the hunk target.

        Parameters
        ----------
        rejig : Rejig
            The parent Rejig instance.
        hunk : Hunk
            The Hunk object to wrap.
        index : int
            Index of this hunk in the parent file.
        parent : PatchFileTarget
            The parent file target.
        """
        super().__init__(rejig)
        self._hunk = hunk
        self._index = index
        self._parent = parent

    @property
    def hunk(self) -> Hunk:
        """The underlying Hunk object."""
        return self._hunk

    @property
    def index(self) -> int:
        """Index of this hunk in the file."""
        return self._index

    def exists(self) -> bool:
        """Check if this hunk has changes."""
        return bool(self._hunk.changes)

    @property
    def old_start(self) -> int:
        """Starting line in original file."""
        return self._hunk.old_start

    @property
    def old_count(self) -> int:
        """Line count in original file."""
        return self._hunk.old_count

    @property
    def new_start(self) -> int:
        """Starting line in new file."""
        return self._hunk.new_start

    @property
    def new_count(self) -> int:
        """Line count in new file."""
        return self._hunk.new_count

    @property
    def function_context(self) -> str | None:
        """Function context from @@ line."""
        return self._hunk.function_context

    @property
    def additions_count(self) -> int:
        """Number of added lines."""
        return self._hunk.additions_count

    @property
    def deletions_count(self) -> int:
        """Number of deleted lines."""
        return self._hunk.deletions_count

    # ===== Operations =====

    def apply(self) -> Result:
        """Apply this hunk's changes.

        Note: Applying individual hunks can be tricky with line
        numbers shifting. Use with caution.

        Returns
        -------
        Result
            Result of applying the hunk.
        """
        path = self._parent.path
        if not path:
            return ErrorResult(
                message="No file path for hunk",
                operation="apply_hunk",
            )

        resolved = self._rejig._resolve_path(path)
        if not resolved.exists():
            return ErrorResult(
                message=f"File does not exist: {resolved}",
                operation="apply_hunk",
            )

        try:
            content = resolved.read_text()
            converter = PatchConverter(self._rejig)
            new_content = converter._apply_hunk(content, self._hunk)

            target = self._rejig.file(resolved)
            return target.rewrite(new_content)
        except Exception as e:
            return ErrorResult(
                message=f"Failed to apply hunk: {e}",
                operation="apply_hunk",
                exception=e,
            )

    def reverse(self) -> PatchHunkTarget:
        """Create a reversed hunk target.

        Returns
        -------
        PatchHunkTarget
            A new target that reverses this hunk.
        """
        reversed_hunk = self._hunk.reverse()
        return PatchHunkTarget(
            self._rejig,
            reversed_hunk,
            self._index,
            self._parent,
        )

    def get_old_content(self) -> str:
        """Get the original content (deletions + context)."""
        return self._hunk.get_old_content()

    def get_new_content(self) -> str:
        """Get the new content (additions + context)."""
        return self._hunk.get_new_content()

    def to_header(self) -> str:
        """Get the @@ header line."""
        return self._hunk.to_header()

    def to_diff_lines(self) -> list[str]:
        """Get the diff lines including header."""
        return self._hunk.to_diff_lines()

    def get_content(self) -> Result:
        """Get the hunk as diff lines.

        Returns
        -------
        Result
            Result with diff lines in data field.
        """
        return Result(
            success=True,
            message=f"Hunk {self._index} @ {self.old_start}",
            data="\n".join(self._hunk.to_diff_lines()),
        )

    def __repr__(self) -> str:
        return (
            f"PatchHunkTarget(#{self._index}, "
            f"@@ -{self.old_start},{self.old_count} "
            f"+{self.new_start},{self.new_count} @@)"
        )
