"""CST parse cache for rejig - avoids re-parsing unchanged files."""
from __future__ import annotations

import os
import threading
from collections import OrderedDict

import libcst as cst


class CSTCache:
    """File-level CST parse cache, invalidated on file modification time changes.

    Uses an LRU eviction strategy and is thread-safe.

    Parameters
    ----------
    max_size : int
        Maximum number of cached parse trees. Defaults to 128.

    Examples
    --------
    >>> cache = CSTCache(max_size=64)
    >>> tree = cache.parse_module("/path/to/file.py")
    >>> # Second call returns cached tree if file hasn't changed
    >>> tree2 = cache.parse_module("/path/to/file.py")
    """

    def __init__(self, max_size: int = 128):
        self._cache: OrderedDict[str, tuple[float, cst.Module]] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get_tree(self, file_path: str) -> cst.Module | None:
        """Get cached parse tree if file hasn't changed.

        Parameters
        ----------
        file_path : str
            Absolute path to the file.

        Returns
        -------
        cst.Module | None
            Cached parse tree, or None if not cached or stale.
        """
        resolved = os.path.realpath(file_path)
        with self._lock:
            if resolved not in self._cache:
                return None
            cached_mtime, tree = self._cache[resolved]
            try:
                current_mtime = os.path.getmtime(resolved)
            except OSError:
                # File was deleted - remove from cache
                del self._cache[resolved]
                return None
            if current_mtime != cached_mtime:
                # File changed - invalidate
                del self._cache[resolved]
                return None
            # Move to end (most recently used)
            self._cache.move_to_end(resolved)
            return tree

    def put_tree(self, file_path: str, tree: cst.Module) -> None:
        """Cache a parse tree with current mtime.

        Parameters
        ----------
        file_path : str
            Absolute path to the file.
        tree : cst.Module
            The parsed CST module.
        """
        resolved = os.path.realpath(file_path)
        try:
            mtime = os.path.getmtime(resolved)
        except OSError:
            return
        with self._lock:
            self._cache[resolved] = (mtime, tree)
            self._cache.move_to_end(resolved)
            # Evict oldest entries if over capacity
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def invalidate(self, file_path: str) -> None:
        """Invalidate cache for a file (call after writing).

        Parameters
        ----------
        file_path : str
            Path to the file to invalidate.
        """
        resolved = os.path.realpath(file_path)
        with self._lock:
            self._cache.pop(resolved, None)

    def clear(self) -> None:
        """Clear entire cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    @property
    def size(self) -> int:
        """Number of cached entries."""
        with self._lock:
            return len(self._cache)

    @property
    def stats(self) -> dict[str, int]:
        """Cache hit/miss statistics."""
        with self._lock:
            return {"hits": self._hits, "misses": self._misses, "size": len(self._cache)}

    def parse_module(self, file_path: str) -> cst.Module:
        """Parse a file, using cache if available.

        Parameters
        ----------
        file_path : str
            Path to the Python file to parse.

        Returns
        -------
        cst.Module
            The parsed CST module.

        Raises
        ------
        FileNotFoundError
            If the file does not exist.
        cst.ParserSyntaxError
            If the file cannot be parsed.
        """
        cached = self.get_tree(file_path)
        if cached is not None:
            with self._lock:
                self._hits += 1
            return cached

        with self._lock:
            self._misses += 1

        content = open(file_path).read()
        tree = cst.parse_module(content)
        self.put_tree(file_path, tree)
        return tree
