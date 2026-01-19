"""Data models for package configuration.

This module defines the core data structures for representing Python package
dependencies and configuration across different formats (requirements.txt,
pyproject.toml, Poetry, UV, etc.).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

# Supported package configuration formats
PackageFormat = Literal["requirements", "pep621", "poetry", "uv"]


@dataclass
class Dependency:
    """Unified representation of a Python dependency.

    Supports parsing from and serializing to multiple formats:
    - pip/requirements.txt
    - PEP 621 pyproject.toml
    - Poetry pyproject.toml

    Parameters
    ----------
    name : str
        Package name (normalized to lowercase with hyphens).
    version_spec : str | None
        Version specification (e.g., ">=1.0,<2.0", "^1.0", "~=1.0").
    extras : list[str]
        Optional extras (e.g., ["security", "async"]).
    markers : str | None
        Environment markers (e.g., "python_version >= '3.10'").
    git_url : str | None
        Git repository URL for VCS dependencies.
    git_ref : str | None
        Git reference (branch, tag, or commit).
    editable : bool
        Whether this is an editable install.
    optional : bool
        Whether this is an optional dependency.
    group : str | None
        Dependency group (e.g., "dev", "test", "docs").

    Examples
    --------
    >>> dep = Dependency.from_pip_line("requests[security]>=2.28.0")
    >>> dep.name
    'requests'
    >>> dep.version_spec
    '>=2.28.0'
    >>> dep.extras
    ['security']
    >>> dep.to_pip_spec()
    'requests[security]>=2.28.0'
    """

    name: str
    version_spec: str | None = None
    extras: list[str] = field(default_factory=list)
    markers: str | None = None
    git_url: str | None = None
    git_ref: str | None = None
    editable: bool = False
    optional: bool = False
    group: str | None = None

    def __post_init__(self) -> None:
        """Normalize the package name."""
        self.name = self._normalize_name(self.name)

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize package name per PEP 503.

        Converts to lowercase and replaces underscores/dots with hyphens.
        """
        return re.sub(r"[-_.]+", "-", name).lower()

    def to_pip_spec(self) -> str:
        """Convert to pip/requirements.txt format.

        Returns
        -------
        str
            Dependency specification in pip format.

        Examples
        --------
        >>> Dependency("requests", ">=2.28.0").to_pip_spec()
        'requests>=2.28.0'
        >>> Dependency("requests", ">=2.28.0", extras=["security"]).to_pip_spec()
        'requests[security]>=2.28.0'
        """
        if self.git_url:
            spec = f"git+{self.git_url}"
            if self.git_ref:
                spec += f"@{self.git_ref}"
            spec += f"#egg={self.name}"
            if self.editable:
                spec = f"-e {spec}"
            return spec

        spec = self.name
        if self.extras:
            spec += f"[{','.join(sorted(self.extras))}]"
        if self.version_spec:
            spec += self.version_spec
        if self.markers:
            spec += f"; {self.markers}"
        return spec

    def to_pep621_spec(self) -> str:
        """Convert to PEP 621 dependency specification.

        Returns
        -------
        str
            Dependency specification for pyproject.toml [project.dependencies].
        """
        # PEP 621 uses the same format as pip for most cases
        return self.to_pip_spec()

    def to_poetry_spec(self) -> str | dict[str, Any]:
        """Convert to Poetry dependency specification.

        Returns
        -------
        str | dict
            Simple version string or dict for complex dependencies.

        Examples
        --------
        >>> Dependency("requests", ">=2.28.0,<3.0").to_poetry_spec()
        '>=2.28.0,<3.0'
        >>> Dependency("requests", ">=2.28.0", extras=["security"]).to_poetry_spec()
        {'version': '>=2.28.0', 'extras': ['security']}
        """
        if self.git_url:
            spec: dict[str, Any] = {"git": self.git_url}
            if self.git_ref:
                spec["rev"] = self.git_ref
            if self.optional:
                spec["optional"] = True
            return spec

        # Simple case: just version
        if not self.extras and not self.markers and not self.optional:
            return self.version_spec or "*"

        # Complex case: dict format
        spec = {}
        if self.version_spec:
            spec["version"] = self.version_spec
        if self.extras:
            spec["extras"] = self.extras
        if self.markers:
            spec["markers"] = self.markers
        if self.optional:
            spec["optional"] = True

        return spec if spec else "*"

    @classmethod
    def from_pip_line(cls, line: str) -> Dependency | None:
        """Parse a dependency from a pip requirements line.

        Parameters
        ----------
        line : str
            A line from requirements.txt or pip-style specification.

        Returns
        -------
        Dependency | None
            Parsed dependency, or None if line is invalid/empty.

        Examples
        --------
        >>> Dependency.from_pip_line("requests>=2.28.0")
        Dependency(name='requests', version_spec='>=2.28.0', ...)
        >>> Dependency.from_pip_line("# comment")
        None
        """
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            return None

        # Skip options like -r, -i, --index-url, etc.
        if line.startswith("-") and not line.startswith("-e "):
            return None

        editable = False
        if line.startswith("-e "):
            editable = True
            line = line[3:].strip()

        # Handle git URLs
        if line.startswith("git+") or "://" in line:
            return cls._parse_vcs_line(line, editable)

        # Parse markers
        markers = None
        if ";" in line:
            line, markers = line.split(";", 1)
            line = line.strip()
            markers = markers.strip()

        # Parse extras
        extras: list[str] = []
        extras_match = re.search(r"\[([^\]]+)\]", line)
        if extras_match:
            extras = [e.strip() for e in extras_match.group(1).split(",")]
            line = line[: extras_match.start()] + line[extras_match.end() :]

        # Parse version spec
        version_match = re.search(r"([<>=!~]+.*)$", line)
        version_spec = None
        if version_match:
            version_spec = version_match.group(1).strip()
            line = line[: version_match.start()]

        name = line.strip()
        if not name:
            return None

        return cls(
            name=name,
            version_spec=version_spec,
            extras=extras,
            markers=markers,
            editable=editable,
        )

    @classmethod
    def _parse_vcs_line(cls, line: str, editable: bool) -> Dependency | None:
        """Parse a VCS dependency line."""
        # Extract egg name
        egg_match = re.search(r"#egg=([^&\s]+)", line)
        if not egg_match:
            # Try to extract name from URL
            url_match = re.search(r"/([^/]+?)(?:\.git)?(?:@|$)", line)
            name = url_match.group(1) if url_match else "unknown"
        else:
            name = egg_match.group(1)

        # Extract git URL and ref
        url = line
        git_ref = None

        # Remove egg fragment
        url = re.sub(r"#egg=[^&\s]+", "", url)

        # Extract @ref
        if "@" in url and "://" in url:
            base_url, rest = url.rsplit("@", 1)
            if "/" not in rest:  # It's a ref, not part of URL
                git_ref = rest
                url = base_url

        # Remove git+ prefix
        if url.startswith("git+"):
            url = url[4:]

        return cls(
            name=name,
            git_url=url,
            git_ref=git_ref,
            editable=editable,
        )

    @classmethod
    def from_pep621(cls, spec: str) -> Dependency:
        """Parse a dependency from PEP 621 format.

        Parameters
        ----------
        spec : str
            Dependency specification from pyproject.toml.

        Returns
        -------
        Dependency
            Parsed dependency.
        """
        # PEP 621 uses PEP 508 format, same as pip
        dep = cls.from_pip_line(spec)
        if dep is None:
            return cls(name=spec)
        return dep

    @classmethod
    def from_poetry(cls, name: str, spec: str | dict[str, Any]) -> Dependency:
        """Parse a dependency from Poetry format.

        Parameters
        ----------
        name : str
            Package name.
        spec : str | dict
            Version string or dict with version/extras/markers.

        Returns
        -------
        Dependency
            Parsed dependency.

        Examples
        --------
        >>> Dependency.from_poetry("requests", "^2.28.0")
        Dependency(name='requests', version_spec='^2.28.0', ...)
        >>> Dependency.from_poetry("requests", {"version": "^2.28.0", "extras": ["security"]})
        Dependency(name='requests', version_spec='^2.28.0', extras=['security'], ...)
        """
        if isinstance(spec, str):
            return cls(name=name, version_spec=spec if spec != "*" else None)

        # Dict format
        version_spec = spec.get("version")
        if version_spec == "*":
            version_spec = None

        return cls(
            name=name,
            version_spec=version_spec,
            extras=spec.get("extras", []),
            markers=spec.get("markers"),
            git_url=spec.get("git"),
            git_ref=spec.get("rev") or spec.get("branch") or spec.get("tag"),
            optional=spec.get("optional", False),
        )


@dataclass
class PackageMetadata:
    """Package metadata from pyproject.toml or setup.py.

    Parameters
    ----------
    name : str | None
        Package name.
    version : str | None
        Package version.
    description : str | None
        Short description.
    authors : list[str]
        List of authors.
    license : str | None
        License identifier.
    python_requires : str | None
        Python version requirement.
    readme : str | None
        Path to README file.
    homepage : str | None
        Project homepage URL.
    repository : str | None
        Repository URL.
    keywords : list[str]
        Package keywords.
    classifiers : list[str]
        PyPI classifiers.
    """

    name: str | None = None
    version: str | None = None
    description: str | None = None
    authors: list[str] = field(default_factory=list)
    license: str | None = None
    python_requires: str | None = None
    readme: str | None = None
    homepage: str | None = None
    repository: str | None = None
    keywords: list[str] = field(default_factory=list)
    classifiers: list[str] = field(default_factory=list)


@dataclass
class PackageConfig:
    """Complete package configuration.

    Represents the full configuration of a Python package, regardless of
    the source format (requirements.txt, pyproject.toml, etc.).

    Parameters
    ----------
    format : PackageFormat
        The format this config was parsed from.
    source_path : Path
        Path to the configuration file.
    metadata : PackageMetadata
        Package metadata.
    dependencies : list[Dependency]
        Main/runtime dependencies.
    dev_dependencies : list[Dependency]
        Development dependencies.
    optional_dependencies : dict[str, list[Dependency]]
        Optional dependency groups.
    scripts : dict[str, str]
        Entry point scripts.
    tool_config : dict[str, dict]
        Tool-specific configuration sections.

    Examples
    --------
    >>> config = PackageConfig(
    ...     format="pep621",
    ...     source_path=Path("pyproject.toml"),
    ...     metadata=PackageMetadata(name="myproject", version="1.0.0"),
    ...     dependencies=[Dependency("requests", ">=2.28.0")],
    ... )
    """

    format: PackageFormat
    source_path: Path
    metadata: PackageMetadata = field(default_factory=PackageMetadata)
    dependencies: list[Dependency] = field(default_factory=list)
    dev_dependencies: list[Dependency] = field(default_factory=list)
    optional_dependencies: dict[str, list[Dependency]] = field(default_factory=dict)
    scripts: dict[str, str] = field(default_factory=dict)
    tool_config: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get_dependency(self, name: str) -> Dependency | None:
        """Find a dependency by name.

        Parameters
        ----------
        name : str
            Package name to find.

        Returns
        -------
        Dependency | None
            The dependency if found, None otherwise.
        """
        normalized = Dependency._normalize_name(name)
        for dep in self.dependencies:
            if dep.name == normalized:
                return dep
        return None

    def get_dev_dependency(self, name: str) -> Dependency | None:
        """Find a dev dependency by name."""
        normalized = Dependency._normalize_name(name)
        for dep in self.dev_dependencies:
            if dep.name == normalized:
                return dep
        return None

    def has_dependency(self, name: str) -> bool:
        """Check if a dependency exists (in any group)."""
        normalized = Dependency._normalize_name(name)
        all_deps = (
            self.dependencies
            + self.dev_dependencies
            + [dep for deps in self.optional_dependencies.values() for dep in deps]
        )
        return any(dep.name == normalized for dep in all_deps)

    def all_dependencies(self, include_dev: bool = True) -> list[Dependency]:
        """Get all dependencies.

        Parameters
        ----------
        include_dev : bool
            Whether to include dev dependencies.

        Returns
        -------
        list[Dependency]
            All dependencies.
        """
        deps = list(self.dependencies)
        if include_dev:
            deps.extend(self.dev_dependencies)
        return deps
