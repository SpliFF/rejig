"""Round-trip TOML I/O backed by tomlkit.

tomlkit parses a file into a document that preserves comments, key order,
whitespace and quote style, and serialises it back unchanged except for the
values that were actually mutated. This is the TOML counterpart to rejig's
ruamel.yaml-backed YAML target: an edit changes only the line(s) it touches
instead of reserialising — and thereby reformatting — the whole file.

All TOML reading and writing in rejig goes through these helpers so the
behaviour is consistent and there is a single TOML backend dependency.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import tomlkit
    from tomlkit.exceptions import TOMLKitError
    from tomlkit.items import Comment, Whitespace
except ImportError:  # pragma: no cover - tomlkit is a declared runtime dependency
    tomlkit = None  # type: ignore[assignment]
    TOMLKitError = Exception  # type: ignore[assignment,misc]
    Comment = Whitespace = ()  # type: ignore[assignment,misc]

# Raised by tomlkit when parsing malformed TOML. Aliased here so callers can
# catch parse errors without importing tomlkit directly; falls back to Exception
# when the backend is unavailable.
TomlError = TOMLKitError


def toml_available() -> bool:
    """Whether the tomlkit backend is importable."""
    return tomlkit is not None


def load_toml(path: str | Path) -> Any:
    """Parse a TOML file into a style-preserving tomlkit document."""
    with open(path, "r", encoding="utf-8") as f:
        return tomlkit.load(f)


def loads_toml(text: str) -> Any:
    """Parse TOML text into a style-preserving tomlkit document."""
    return tomlkit.parse(text)


def _body_of(table: Any) -> Any:
    """Return the tomlkit container body backing ``table``, or None."""
    value = getattr(table, "value", None)
    if value is not None and hasattr(value, "body"):
        return value.body
    return table.body if hasattr(table, "body") else None


def remove_key(table: Any, key: str, *, comments: bool = True) -> bool:
    """Remove ``key`` from ``table``, taking its attached comment block with it.

    A plain ``del table[key]`` removes only the key/value pair. Standalone comments
    are separate items in the tomlkit container, so the lines documenting an entry
    survive it and end up orphaned above whatever follows.

    A comment block counts as *attached* when it sits on the line(s) immediately
    above the key with no blank line between - the usual way a single entry is
    documented. A comment separated from the key by a blank line introduces the
    section rather than the entry, and is left alone. A trailing comment on the
    key's own line is part of that item's trivia and always goes with it.

    One separator blank line is dropped alongside, so the removal does not leave a
    doubled blank between the neighbouring blocks or a stray one against the table
    header.

    Parameters
    ----------
    table : Any
        A tomlkit table or container to remove from.
    key : str
        Key to remove. Must match the key exactly.
    comments : bool
        Whether to take the attached comment block too. Pass False for the plain
        key-only removal.

    Returns
    -------
    bool
        True if the key was found and removed.

    Examples
    --------
    >>> remove_key(doc["tool"]["poetry"]["dependencies"], "sqlparse")
    True
    """
    body = _body_of(table)
    if body is None:
        # Not a tomlkit container (e.g. a plain dict): nothing to preserve.
        if key in table:
            del table[key]
            return True
        return False

    index = next(
        (i for i, (k, _) in enumerate(body) if k is not None and k.key == key), None
    )
    if index is None:
        return False

    start = end = index
    if comments:
        while start > 0:
            prev_key, prev_item = body[start - 1]
            if prev_key is None and isinstance(prev_item, Comment):
                start -= 1
            else:
                break

    before_blank = start > 0 and isinstance(body[start - 1][1], Whitespace)
    after_blank = end + 1 < len(body) and isinstance(body[end + 1][1], Whitespace)
    if before_blank and (after_blank or end + 1 == len(body)):
        start -= 1
    elif after_blank and start == 0:
        end += 1

    del body[start : end + 1]
    return True


def dump_toml(document: Any, path: str | Path) -> None:
    """Write a tomlkit document (or plain mapping) back to ``path``.

    Pass the document returned by :func:`load_toml`/:func:`loads_toml`, mutated
    in place, to preserve comments and layout on every untouched line. A plain
    mapping is accepted too (tomlkit converts it), but has no styling to retain.
    """
    with open(path, "w", encoding="utf-8") as f:
        tomlkit.dump(document, f)