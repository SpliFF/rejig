"""Parser for unified and git diff formats.

This module provides the PatchParser class for parsing diff text into
structured Patch objects.

Supported formats:
- Standard unified diff (diff -u)
- Git extended diff format (git diff, git format-patch)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import ErrorResult, Result
from rejig.patching.models import (
    Change,
    ChangeType,
    FilePatch,
    Hunk,
    Patch,
    PatchFormat,
)

if TYPE_CHECKING:
    pass


class PatchParser:
    """Parser for unified diff and git diff formats.

    Parses diff text into structured Patch objects that can be
    manipulated and applied.

    Examples
    --------
    >>> parser = PatchParser()
    >>> patch = parser.parse(diff_text)
    >>> print(patch.file_count)
    3
    >>> print(patch.total_additions)
    42

    >>> # Parse from file
    >>> patch = parser.parse_file(Path("changes.patch"))
    """

    # Regex patterns for parsing
    _HUNK_HEADER = re.compile(
        r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?:\s+(.*))?$"
    )
    _UNIFIED_FILE_OLD = re.compile(r"^--- (.+?)(?:\t.*)?$")
    _UNIFIED_FILE_NEW = re.compile(r"^\+\+\+ (.+?)(?:\t.*)?$")
    _GIT_DIFF_HEADER = re.compile(r"^diff --git a/(.+) b/(.+)$")
    _GIT_OLD_MODE = re.compile(r"^old mode (\d+)$")
    _GIT_NEW_MODE = re.compile(r"^new mode (\d+)$")
    _GIT_DELETED_FILE = re.compile(r"^deleted file mode (\d+)$")
    _GIT_NEW_FILE = re.compile(r"^new file mode (\d+)$")
    _GIT_RENAME_FROM = re.compile(r"^rename from (.+)$")
    _GIT_RENAME_TO = re.compile(r"^rename to (.+)$")
    _GIT_SIMILARITY = re.compile(r"^similarity index (\d+)%$")
    _GIT_INDEX = re.compile(r"^index [a-f0-9]+\.\.[a-f0-9]+(?:\s+\d+)?$")
    _GIT_BINARY = re.compile(r"^Binary files .+ and .+ differ$")

    def parse(self, patch_text: str) -> Patch:
        """Parse a diff string into a Patch object.

        Parameters
        ----------
        patch_text : str
            The diff text to parse (unified or git format).

        Returns
        -------
        Patch
            Parsed patch object containing all file changes.
        """
        if not patch_text.strip():
            return Patch()

        lines = patch_text.splitlines()
        patch_format = self._detect_format(lines)

        files = []
        current_file: FilePatch | None = None
        current_hunk: Hunk | None = None

        i = 0
        while i < len(lines):
            line = lines[i]

            # Git diff header
            git_match = self._GIT_DIFF_HEADER.match(line)
            if git_match:
                # Save previous file
                if current_file is not None:
                    if current_hunk is not None:
                        current_file.hunks.append(current_hunk)
                    files.append(current_file)

                current_file = FilePatch(
                    old_path=Path(git_match.group(1)),
                    new_path=Path(git_match.group(2)),
                )
                current_hunk = None
                i += 1
                continue

            # Git extended headers
            if current_file is not None:
                if self._GIT_NEW_FILE.match(line):
                    current_file.is_new = True
                    current_file.old_path = None
                    i += 1
                    continue
                if self._GIT_DELETED_FILE.match(line):
                    current_file.is_deleted = True
                    current_file.new_path = None
                    i += 1
                    continue
                old_mode = self._GIT_OLD_MODE.match(line)
                if old_mode:
                    current_file.old_mode = old_mode.group(1)
                    i += 1
                    continue
                new_mode = self._GIT_NEW_MODE.match(line)
                if new_mode:
                    current_file.new_mode = new_mode.group(1)
                    i += 1
                    continue
                rename_from = self._GIT_RENAME_FROM.match(line)
                if rename_from:
                    current_file.is_renamed = True
                    current_file.old_path = Path(rename_from.group(1))
                    i += 1
                    continue
                rename_to = self._GIT_RENAME_TO.match(line)
                if rename_to:
                    current_file.new_path = Path(rename_to.group(1))
                    i += 1
                    continue
                similarity = self._GIT_SIMILARITY.match(line)
                if similarity:
                    current_file.similarity_index = int(similarity.group(1))
                    i += 1
                    continue
                if self._GIT_INDEX.match(line):
                    i += 1
                    continue
                if self._GIT_BINARY.match(line):
                    current_file.is_binary = True
                    i += 1
                    continue

            # Unified diff file headers (--- / +++)
            old_match = self._UNIFIED_FILE_OLD.match(line)
            if old_match:
                old_path_str = old_match.group(1)
                # Handle /dev/null for new files
                if old_path_str == "/dev/null":
                    old_path = None
                else:
                    # Remove a/ prefix if present
                    if old_path_str.startswith("a/"):
                        old_path_str = old_path_str[2:]
                    old_path = Path(old_path_str)

                # Check if this is a new file (not git format)
                # If we already have hunks or a different old_path, this is a new file
                if current_file is not None and (
                    current_file.hunks or
                    (current_file.old_path is not None and current_file.old_path != old_path)
                ):
                    # Save previous file and start new one
                    if current_hunk is not None:
                        current_file.hunks.append(current_hunk)
                        current_hunk = None
                    files.append(current_file)
                    current_file = FilePatch(old_path=old_path)
                elif current_file is None:
                    current_file = FilePatch(old_path=old_path)
                elif current_file.old_path is None and not current_file.is_new:
                    current_file.old_path = old_path

                if old_path is None and current_file is not None:
                    current_file.is_new = True
                    current_file.old_path = None

                i += 1
                continue

            new_match = self._UNIFIED_FILE_NEW.match(line)
            if new_match:
                new_path_str = new_match.group(1)
                # Handle /dev/null for deleted files
                if new_path_str == "/dev/null":
                    new_path = None
                else:
                    # Remove b/ prefix if present
                    if new_path_str.startswith("b/"):
                        new_path_str = new_path_str[2:]
                    new_path = Path(new_path_str)

                if current_file is None:
                    # Start new file from +++ line (non-git format)
                    current_file = FilePatch(new_path=new_path)
                else:
                    current_file.new_path = new_path

                if new_path is None and current_file is not None:
                    current_file.is_deleted = True
                    current_file.new_path = None

                i += 1
                continue

            # Hunk header
            hunk_match = self._HUNK_HEADER.match(line)
            if hunk_match:
                # Save previous hunk
                if current_hunk is not None and current_file is not None:
                    current_file.hunks.append(current_hunk)

                old_start = int(hunk_match.group(1))
                old_count = int(hunk_match.group(2)) if hunk_match.group(2) else 1
                new_start = int(hunk_match.group(3))
                new_count = int(hunk_match.group(4)) if hunk_match.group(4) else 1
                func_context = hunk_match.group(5)

                current_hunk = Hunk(
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count,
                    function_context=func_context if func_context else None,
                )
                i += 1
                continue

            # Change lines (+, -, space)
            if current_hunk is not None:
                if line.startswith("+"):
                    current_hunk.changes.append(Change(
                        type=ChangeType.ADD,
                        content=line[1:],
                    ))
                    i += 1
                    continue
                elif line.startswith("-"):
                    current_hunk.changes.append(Change(
                        type=ChangeType.DELETE,
                        content=line[1:],
                    ))
                    i += 1
                    continue
                elif line.startswith(" ") or line == "":
                    # Context line (space prefix) or empty line
                    content = line[1:] if line.startswith(" ") else ""
                    current_hunk.changes.append(Change(
                        type=ChangeType.CONTEXT,
                        content=content,
                    ))
                    i += 1
                    continue
                elif line.startswith("\\"):
                    # "\ No newline at end of file" - skip
                    i += 1
                    continue

            # Skip unrecognized lines
            i += 1

        # Save final file and hunk
        if current_file is not None:
            if current_hunk is not None:
                current_file.hunks.append(current_hunk)
            files.append(current_file)

        # Assign line numbers to changes
        for file_patch in files:
            for hunk in file_patch.hunks:
                self._assign_line_numbers(hunk)

        return Patch(files=files, format=patch_format)

    def parse_file(self, path: Path) -> Patch | None:
        """Parse a patch file.

        Parameters
        ----------
        path : Path
            Path to the patch file.

        Returns
        -------
        Patch | None
            Parsed patch, or None if file doesn't exist or is empty.
        """
        if not path.exists():
            return None

        content = path.read_text()
        if not content.strip():
            return None

        return self.parse(content)

    def parse_to_result(self, patch_text: str) -> Result:
        """Parse a patch and return a Result object.

        This method follows rejig's pattern of returning Result objects
        instead of raising exceptions.

        Parameters
        ----------
        patch_text : str
            The diff text to parse.

        Returns
        -------
        Result
            Result containing the parsed Patch in data field,
            or ErrorResult on failure.
        """
        try:
            patch = self.parse(patch_text)
            return Result(
                success=True,
                message=f"Parsed patch with {patch.file_count} file(s)",
                data=patch,
            )
        except Exception as e:
            return ErrorResult(
                message=f"Failed to parse patch: {e}",
                operation="parse",
                exception=e,
            )

    def _detect_format(self, lines: list[str]) -> PatchFormat:
        """Detect whether this is a git or unified diff."""
        for line in lines[:20]:  # Check first 20 lines
            if line.startswith("diff --git"):
                return PatchFormat.GIT
        return PatchFormat.UNIFIED

    def _assign_line_numbers(self, hunk: Hunk) -> None:
        """Assign line numbers to changes in a hunk."""
        old_line = hunk.old_start
        new_line = hunk.new_start

        for change in hunk.changes:
            if change.type == ChangeType.CONTEXT:
                change.old_line = old_line
                change.new_line = new_line
                old_line += 1
                new_line += 1
            elif change.type == ChangeType.DELETE:
                change.old_line = old_line
                change.new_line = None
                old_line += 1
            elif change.type == ChangeType.ADD:
                change.old_line = None
                change.new_line = new_line
                new_line += 1


def parse_patch(patch_text: str) -> Patch:
    """Convenience function to parse a patch string.

    Parameters
    ----------
    patch_text : str
        The diff text to parse.

    Returns
    -------
    Patch
        Parsed patch object.
    """
    return PatchParser().parse(patch_text)


def parse_patch_file(path: Path | str) -> Patch | None:
    """Convenience function to parse a patch file.

    Parameters
    ----------
    path : Path | str
        Path to the patch file.

    Returns
    -------
    Patch | None
        Parsed patch, or None if file doesn't exist.
    """
    return PatchParser().parse_file(Path(path) if isinstance(path, str) else path)
