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
except ImportError:  # pragma: no cover - tomlkit is a declared runtime dependency
    tomlkit = None  # type: ignore[assignment]
    TOMLKitError = Exception  # type: ignore[assignment,misc]

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


def dump_toml(document: Any, path: str | Path) -> None:
    """Write a tomlkit document (or plain mapping) back to ``path``.

    Pass the document returned by :func:`load_toml`/:func:`loads_toml`, mutated
    in place, to preserve comments and layout on every untouched line. A plain
    mapping is accepted too (tomlkit converts it), but has no styling to retain.
    """
    with open(path, "w", encoding="utf-8") as f:
        tomlkit.dump(document, f)