"""Data models for patch representation.

This module defines the core dataclasses for representing unified diffs:
- Change - A single line addition, deletion, or context line
- Hunk - A contiguous block of changes with line number info
- FilePatch - All hunks for a single file
- Patch - Collection of file patches from a diff
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterator, Literal


class PatchFormat(Enum):
    """Format of the patch."""

    UNIFIED = "unified"  # Standard unified diff (diff -u)
    GIT = "git"  # Git extended format (git diff)


class ChangeType(Enum):
    """Type of change in a diff line."""

    ADD = "add"
    DELETE = "delete"
    CONTEXT = "context"


@dataclass
class Change:
    """A single line change in a hunk.

    Represents one line from a unified diff:
    - '+' lines are additions (type=ADD)
    - '-' lines are deletions (type=DELETE)
    - ' ' lines are context (type=CONTEXT)

    Attributes:
        type: Type of change (add, delete, context)
        content: The line content (without +/- prefix)
        old_line: Line number in original file (None for additions)
        new_line: Line number in new file (None for deletions)
    """

    type: ChangeType
    content: str
    old_line: int | None = None
    new_line: int | None = None

    @property
    def is_addition(self) -> bool:
        """Check if this is an added line."""
        return self.type == ChangeType.ADD

    @property
    def is_deletion(self) -> bool:
        """Check if this is a deleted line."""
        return self.type == ChangeType.DELETE

    @property
    def is_context(self) -> bool:
        """Check if this is a context line."""
        return self.type == ChangeType.CONTEXT

    def to_diff_line(self) -> str:
        """Convert back to a diff line with prefix."""
        prefix = {
            ChangeType.ADD: "+",
            ChangeType.DELETE: "-",
            ChangeType.CONTEXT: " ",
        }[self.type]
        return f"{prefix}{self.content}"


@dataclass
class Hunk:
    """A contiguous block of changes in a file.

    A hunk represents one @@ section from a unified diff. It contains
    the line range information and the actual changes.

    Attributes:
        old_start: Starting line number in original file
        old_count: Number of lines from original file
        new_start: Starting line number in new file
        new_count: Number of lines in new file
        changes: List of changes in this hunk
        function_context: Optional function context from @@ line (e.g., "def foo()")
    """

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    changes: list[Change] = field(default_factory=list)
    function_context: str | None = None

    @property
    def additions(self) -> list[Change]:
        """Get all added lines."""
        return [c for c in self.changes if c.is_addition]

    @property
    def deletions(self) -> list[Change]:
        """Get all deleted lines."""
        return [c for c in self.changes if c.is_deletion]

    @property
    def additions_count(self) -> int:
        """Count of added lines."""
        return len(self.additions)

    @property
    def deletions_count(self) -> int:
        """Count of deleted lines."""
        return len(self.deletions)

    def to_header(self) -> str:
        """Generate the @@ header line."""
        header = f"@@ -{self.old_start},{self.old_count} +{self.new_start},{self.new_count} @@"
        if self.function_context:
            header += f" {self.function_context}"
        return header

    def to_diff_lines(self) -> list[str]:
        """Convert hunk to diff lines including header."""
        lines = [self.to_header()]
        lines.extend(c.to_diff_line() for c in self.changes)
        return lines

    def reverse(self) -> Hunk:
        """Create a reversed hunk (swap additions/deletions)."""
        reversed_changes = []
        for change in self.changes:
            if change.is_addition:
                reversed_changes.append(Change(
                    type=ChangeType.DELETE,
                    content=change.content,
                    old_line=change.new_line,
                    new_line=None,
                ))
            elif change.is_deletion:
                reversed_changes.append(Change(
                    type=ChangeType.ADD,
                    content=change.content,
                    old_line=None,
                    new_line=change.old_line,
                ))
            else:
                # Context lines swap line numbers
                reversed_changes.append(Change(
                    type=ChangeType.CONTEXT,
                    content=change.content,
                    old_line=change.new_line,
                    new_line=change.old_line,
                ))

        return Hunk(
            old_start=self.new_start,
            old_count=self.new_count,
            new_start=self.old_start,
            new_count=self.old_count,
            changes=reversed_changes,
            function_context=self.function_context,
        )

    def get_old_content(self) -> str:
        """Get the original content (deletions + context)."""
        lines = []
        for change in self.changes:
            if change.is_deletion or change.is_context:
                lines.append(change.content)
        return "\n".join(lines)

    def get_new_content(self) -> str:
        """Get the new content (additions + context)."""
        lines = []
        for change in self.changes:
            if change.is_addition or change.is_context:
                lines.append(change.content)
        return "\n".join(lines)


@dataclass
class FilePatch:
    """All changes to a single file.

    Contains metadata about the file and all hunks of changes.

    Attributes:
        old_path: Path in original version (None for new files)
        new_path: Path in new version (None for deleted files)
        hunks: List of change hunks
        is_new: Whether this is a new file
        is_deleted: Whether this file is deleted
        is_renamed: Whether this file is renamed
        is_binary: Whether this is a binary file
        old_mode: Original file mode (git extended)
        new_mode: New file mode (git extended)
        similarity_index: Similarity percentage for renames (git extended)
    """

    old_path: Path | None = None
    new_path: Path | None = None
    hunks: list[Hunk] = field(default_factory=list)
    is_new: bool = False
    is_deleted: bool = False
    is_renamed: bool = False
    is_binary: bool = False
    old_mode: str | None = None
    new_mode: str | None = None
    similarity_index: int | None = None

    @property
    def path(self) -> Path | None:
        """Get the primary path (new_path for additions, old_path for deletions)."""
        return self.new_path or self.old_path

    @property
    def additions_count(self) -> int:
        """Total added lines across all hunks."""
        return sum(h.additions_count for h in self.hunks)

    @property
    def deletions_count(self) -> int:
        """Total deleted lines across all hunks."""
        return sum(h.deletions_count for h in self.hunks)

    @property
    def has_changes(self) -> bool:
        """Check if file has any changes."""
        return bool(self.hunks) or self.is_new or self.is_deleted or self.is_renamed

    def to_header_lines(self) -> list[str]:
        """Generate diff header lines for this file."""
        lines = []

        # Git extended format headers
        if self.is_new:
            lines.append(f"diff --git a/{self.new_path} b/{self.new_path}")
            lines.append("new file mode 100644")
            lines.append("--- /dev/null")
            lines.append(f"+++ b/{self.new_path}")
        elif self.is_deleted:
            lines.append(f"diff --git a/{self.old_path} b/{self.old_path}")
            lines.append("deleted file mode 100644")
            lines.append(f"--- a/{self.old_path}")
            lines.append("+++ /dev/null")
        elif self.is_renamed:
            lines.append(f"diff --git a/{self.old_path} b/{self.new_path}")
            if self.similarity_index is not None:
                lines.append(f"similarity index {self.similarity_index}%")
            lines.append(f"rename from {self.old_path}")
            lines.append(f"rename to {self.new_path}")
            if self.hunks:
                lines.append(f"--- a/{self.old_path}")
                lines.append(f"+++ b/{self.new_path}")
        else:
            # Standard unified diff
            old = self.old_path or self.new_path
            new = self.new_path or self.old_path
            lines.append(f"--- a/{old}")
            lines.append(f"+++ b/{new}")

        return lines

    def to_unified_diff(self) -> str:
        """Convert to unified diff format."""
        lines = self.to_header_lines()
        for hunk in self.hunks:
            lines.extend(hunk.to_diff_lines())
        return "\n".join(lines)

    def reverse(self) -> FilePatch:
        """Create a reversed file patch."""
        return FilePatch(
            old_path=self.new_path,
            new_path=self.old_path,
            hunks=[h.reverse() for h in self.hunks],
            is_new=self.is_deleted,
            is_deleted=self.is_new,
            is_renamed=self.is_renamed,
            is_binary=self.is_binary,
            old_mode=self.new_mode,
            new_mode=self.old_mode,
            similarity_index=self.similarity_index,
        )


@dataclass
class Patch:
    """A complete patch containing changes to one or more files.

    This is the top-level container for parsed diff content.

    Attributes:
        files: List of file patches
        format: The format of the original patch (unified or git)
    """

    files: list[FilePatch] = field(default_factory=list)
    format: PatchFormat = PatchFormat.UNIFIED

    def __iter__(self) -> Iterator[FilePatch]:
        """Iterate over file patches."""
        return iter(self.files)

    def __len__(self) -> int:
        """Number of files in the patch."""
        return len(self.files)

    def __bool__(self) -> bool:
        """Check if patch has any files."""
        return bool(self.files)

    @property
    def file_count(self) -> int:
        """Number of files in the patch."""
        return len(self.files)

    @property
    def total_additions(self) -> int:
        """Total added lines across all files."""
        return sum(f.additions_count for f in self.files)

    @property
    def total_deletions(self) -> int:
        """Total deleted lines across all files."""
        return sum(f.deletions_count for f in self.files)

    @property
    def paths(self) -> list[Path]:
        """Get all file paths affected by this patch."""
        paths = []
        for fp in self.files:
            if fp.path:
                paths.append(fp.path)
        return paths

    @property
    def new_files(self) -> list[FilePatch]:
        """Get all new file additions."""
        return [f for f in self.files if f.is_new]

    @property
    def deleted_files(self) -> list[FilePatch]:
        """Get all file deletions."""
        return [f for f in self.files if f.is_deleted]

    @property
    def renamed_files(self) -> list[FilePatch]:
        """Get all file renames."""
        return [f for f in self.files if f.is_renamed]

    @property
    def modified_files(self) -> list[FilePatch]:
        """Get all modified (not new/deleted/renamed) files."""
        return [f for f in self.files if not f.is_new and not f.is_deleted and not f.is_renamed]

    def get_file(self, path: Path | str) -> FilePatch | None:
        """Get the file patch for a specific path.

        Parameters
        ----------
        path : Path | str
            The path to look up.

        Returns
        -------
        FilePatch | None
            The file patch, or None if not found.
        """
        path = Path(path) if isinstance(path, str) else path
        for fp in self.files:
            if fp.old_path == path or fp.new_path == path:
                return fp
        return None

    def reverse(self) -> Patch:
        """Create a reversed patch (undo).

        Returns
        -------
        Patch
            A new patch that reverses all changes.
        """
        return Patch(
            files=[f.reverse() for f in self.files],
            format=self.format,
        )

    def to_unified_diff(self) -> str:
        """Convert to unified diff format.

        Returns
        -------
        str
            The complete patch as a unified diff string.
        """
        sections = []
        for fp in self.files:
            sections.append(fp.to_unified_diff())
        return "\n".join(sections)

    def summary(self) -> str:
        """Generate a human-readable summary.

        Returns
        -------
        str
            Summary of the patch contents.
        """
        lines = [
            f"Patch: {len(self.files)} file(s)",
            f"  +{self.total_additions}/-{self.total_deletions} lines",
        ]
        if self.new_files:
            lines.append(f"  New: {len(self.new_files)}")
        if self.deleted_files:
            lines.append(f"  Deleted: {len(self.deleted_files)}")
        if self.renamed_files:
            lines.append(f"  Renamed: {len(self.renamed_files)}")
        if self.modified_files:
            lines.append(f"  Modified: {len(self.modified_files)}")

        lines.append("Files:")
        for fp in self.files:
            status = ""
            if fp.is_new:
                status = " (new)"
            elif fp.is_deleted:
                status = " (deleted)"
            elif fp.is_renamed:
                status = f" (renamed from {fp.old_path})"

            path = fp.path or fp.old_path or fp.new_path
            lines.append(f"  {path}{status}: +{fp.additions_count}/-{fp.deletions_count}")

        return "\n".join(lines)
