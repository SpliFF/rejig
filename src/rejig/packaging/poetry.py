"""Poetry pyproject.toml parser.

Parses Poetry-specific pyproject.toml configuration.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rejig.packaging.models import Dependency, PackageConfig, PackageMetadata
from rejig.core.results import Result

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig

# Python 3.11+ has tomllib built-in
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore

try:
    import tomli_w
except ImportError:
    tomli_w = None  # type: ignore


class PoetryParser:
    """Parser for Poetry pyproject.toml files.

    Parses the [tool.poetry] section with Poetry-specific syntax including:
    - Version constraints: ^1.0, ~1.0, >=1.0,<2.0
    - Dict format: {version = "^1.0", extras = ["security"]}
    - Git dependencies: {git = "...", branch = "main"}
    - Optional dependencies
    - Dependency groups

    Parameters
    ----------
    rejig : Rejig | None
        Optional Rejig instance.

    Examples
    --------
    >>> parser = PoetryParser()
    >>> config = parser.parse(Path("pyproject.toml"))
    >>> print(config.metadata.name)
    myproject
    """

    def __init__(self, rejig: Rejig | None = None) -> None:
        self._rejig = rejig

    def parse(self, path: Path) -> PackageConfig | None:
        """Parse a Poetry pyproject.toml file.

        Parameters
        ----------
        path : Path
            Path to the pyproject.toml file.

        Returns
        -------
        PackageConfig | None
            Parsed configuration, or None if parsing failed.
        """
        if tomllib is None:
            return None

        if not path.exists():
            return None

        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except Exception:
            return None

        # Must have [tool.poetry] section
        poetry = data.get("tool", {}).get("poetry")
        if not poetry:
            return None

        return self._parse_data(data, path)

    def _parse_data(self, data: dict[str, Any], path: Path) -> PackageConfig:
        """Parse loaded TOML data into PackageConfig."""
        poetry = data.get("tool", {}).get("poetry", {})

        # Parse metadata
        metadata = self._parse_metadata(poetry)

        # Parse main dependencies (excluding python)
        dependencies: list[Dependency] = []
        for name, spec in poetry.get("dependencies", {}).items():
            if name.lower() == "python":
                # Extract python version requirement
                if isinstance(spec, str):
                    metadata.python_requires = self._poetry_to_pep440(spec)
                continue
            dep = Dependency.from_poetry(name, spec)
            dependencies.append(dep)

        # Parse dev dependencies (old style)
        dev_dependencies: list[Dependency] = []
        for name, spec in poetry.get("dev-dependencies", {}).items():
            dep = Dependency.from_poetry(name, spec)
            dep.group = "dev"
            dev_dependencies.append(dep)

        # Parse dependency groups (new style)
        optional_deps: dict[str, list[Dependency]] = {}
        for group_name, group_data in poetry.get("group", {}).items():
            group_deps: list[Dependency] = []
            deps_section = group_data.get("dependencies", {})
            for name, spec in deps_section.items():
                dep = Dependency.from_poetry(name, spec)
                dep.group = group_name
                group_deps.append(dep)

            optional_deps[group_name] = group_deps

            # Also add to dev_dependencies if it's a dev-like group
            if group_name in ("dev", "development", "test", "testing"):
                dev_dependencies.extend(group_deps)

        # Parse extras as optional dependencies
        for extra_name, extra_deps in poetry.get("extras", {}).items():
            extra_list: list[Dependency] = []
            for dep_name in extra_deps:
                # Find in main dependencies
                for dep in dependencies:
                    if dep.name == Dependency._normalize_name(dep_name):
                        extra_list.append(dep)
                        break
            if extra_list:
                optional_deps[extra_name] = extra_list

        # Parse scripts
        scripts = dict(poetry.get("scripts", {}))

        # Collect tool config (excluding poetry itself)
        tool_config = {k: v for k, v in data.get("tool", {}).items() if k != "poetry"}

        return PackageConfig(
            format="poetry",
            source_path=path,
            metadata=metadata,
            dependencies=dependencies,
            dev_dependencies=dev_dependencies,
            optional_dependencies=optional_deps,
            scripts=scripts,
            tool_config=tool_config,
        )

    def _parse_metadata(self, poetry: dict[str, Any]) -> PackageMetadata:
        """Parse project metadata from [tool.poetry] section."""
        authors: list[str] = poetry.get("authors", [])

        license_info = poetry.get("license")

        urls = poetry.get("urls", {})
        homepage = poetry.get("homepage") or urls.get("Homepage")
        repository = poetry.get("repository") or urls.get("Repository")

        return PackageMetadata(
            name=poetry.get("name"),
            version=poetry.get("version"),
            description=poetry.get("description"),
            authors=authors,
            license=license_info,
            readme=poetry.get("readme"),
            homepage=homepage,
            repository=repository,
            keywords=poetry.get("keywords", []),
            classifiers=poetry.get("classifiers", []),
        )

    def _poetry_to_pep440(self, version: str) -> str:
        """Convert Poetry version constraint to PEP 440.

        Parameters
        ----------
        version : str
            Poetry version constraint (e.g., "^3.10", "~3.10").

        Returns
        -------
        str
            PEP 440 compatible version constraint.
        """
        version = version.strip()

        # Handle caret (^) - compatible release
        if version.startswith("^"):
            base = version[1:]
            parts = base.split(".")
            if len(parts) >= 2:
                major = int(parts[0])
                if major == 0:
                    # ^0.x means >=0.x,<0.(x+1)
                    if len(parts) >= 2:
                        minor = int(parts[1])
                        return f">={base},<0.{minor + 1}.0"
                else:
                    # ^x.y means >=x.y,<(x+1).0.0
                    return f">={base},<{major + 1}.0.0"
            return f">={base}"

        # Handle tilde (~) - approximately equivalent
        if version.startswith("~"):
            base = version[1:]
            parts = base.split(".")
            if len(parts) >= 2:
                major = parts[0]
                minor = int(parts[1])
                return f">={base},<{major}.{minor + 1}.0"
            return f">={base}"

        # Already PEP 440 compatible
        return version

    def add_dependency(
        self,
        path: Path,
        name: str,
        version: str | None = None,
        dev: bool = False,
        group: str | None = None,
        dry_run: bool = False,
    ) -> Result:
        """Add a dependency to Poetry pyproject.toml.

        Parameters
        ----------
        path : Path
            Path to pyproject.toml.
        name : str
            Package name.
        version : str | None
            Version specification (Poetry format).
        dev : bool
            Whether this is a dev dependency.
        group : str | None
            Dependency group name.
        dry_run : bool
            If True, don't write changes.

        Returns
        -------
        Result
            Result of the operation.
        """
        if tomllib is None or tomli_w is None:
            return Result(
                success=False,
                message="tomllib and tomli-w are required for pyproject.toml operations",
            )

        if not path.exists():
            return Result(success=False, message=f"File not found: {path}")

        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            return Result(success=False, message=f"Failed to parse TOML: {e}")

        spec = version or "*"

        # Ensure tool.poetry exists
        if "tool" not in data:
            data["tool"] = {}
        if "poetry" not in data["tool"]:
            data["tool"]["poetry"] = {}

        poetry = data["tool"]["poetry"]

        if group:
            # Add to dependency group
            if "group" not in poetry:
                poetry["group"] = {}
            if group not in poetry["group"]:
                poetry["group"][group] = {"dependencies": {}}
            if "dependencies" not in poetry["group"][group]:
                poetry["group"][group]["dependencies"] = {}

            deps_dict = poetry["group"][group]["dependencies"]
        elif dev:
            # Add to dev group (new style)
            if "group" not in poetry:
                poetry["group"] = {}
            if "dev" not in poetry["group"]:
                poetry["group"]["dev"] = {"dependencies": {}}
            if "dependencies" not in poetry["group"]["dev"]:
                poetry["group"]["dev"]["dependencies"] = {}

            deps_dict = poetry["group"]["dev"]["dependencies"]
        else:
            # Add to main dependencies
            if "dependencies" not in poetry:
                poetry["dependencies"] = {}
            deps_dict = poetry["dependencies"]

        # Check if already exists
        normalized = Dependency._normalize_name(name)
        for existing_name in deps_dict:
            if Dependency._normalize_name(existing_name) == normalized:
                return Result(success=True, message=f"Dependency {name} already exists")

        deps_dict[name] = spec

        if dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add {name} = {spec!r} to {path}",
                files_changed=[path],
            )

        try:
            with open(path, "wb") as f:
                tomli_w.dump(data, f)
            return Result(
                success=True,
                message=f"Added {name} = {spec!r} to {path}",
                files_changed=[path],
            )
        except Exception as e:
            return Result(success=False, message=f"Failed to write TOML: {e}")

    def remove_dependency(
        self, path: Path, name: str, dry_run: bool = False
    ) -> Result:
        """Remove a dependency from Poetry pyproject.toml.

        Parameters
        ----------
        path : Path
            Path to pyproject.toml.
        name : str
            Package name to remove.
        dry_run : bool
            If True, don't write changes.

        Returns
        -------
        Result
            Result of the operation.
        """
        if tomllib is None or tomli_w is None:
            return Result(
                success=False,
                message="tomllib and tomli-w are required for pyproject.toml operations",
            )

        if not path.exists():
            return Result(success=False, message=f"File not found: {path}")

        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            return Result(success=False, message=f"Failed to parse TOML: {e}")

        poetry = data.get("tool", {}).get("poetry", {})
        normalized = Dependency._normalize_name(name)
        found = False

        # Check main dependencies
        if "dependencies" in poetry:
            to_remove = None
            for dep_name in poetry["dependencies"]:
                if Dependency._normalize_name(dep_name) == normalized:
                    to_remove = dep_name
                    found = True
                    break
            if to_remove:
                del poetry["dependencies"][to_remove]

        # Check dev-dependencies (old style)
        if "dev-dependencies" in poetry:
            to_remove = None
            for dep_name in poetry["dev-dependencies"]:
                if Dependency._normalize_name(dep_name) == normalized:
                    to_remove = dep_name
                    found = True
                    break
            if to_remove:
                del poetry["dev-dependencies"][to_remove]

        # Check dependency groups
        if "group" in poetry:
            for group_name in poetry["group"]:
                group_deps = poetry["group"][group_name].get("dependencies", {})
                to_remove = None
                for dep_name in group_deps:
                    if Dependency._normalize_name(dep_name) == normalized:
                        to_remove = dep_name
                        found = True
                        break
                if to_remove:
                    del group_deps[to_remove]

        if not found:
            return Result(success=True, message=f"Dependency {name} not found")

        if dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would remove {name} from {path}",
                files_changed=[path],
            )

        try:
            with open(path, "wb") as f:
                tomli_w.dump(data, f)
            return Result(
                success=True,
                message=f"Removed {name} from {path}",
                files_changed=[path],
            )
        except Exception as e:
            return Result(success=False, message=f"Failed to write TOML: {e}")


def parse_poetry(path: Path) -> PackageConfig | None:
    """Convenience function to parse a Poetry pyproject.toml.

    Parameters
    ----------
    path : Path
        Path to pyproject.toml.

    Returns
    -------
    PackageConfig | None
        Parsed configuration, or None if parsing failed.
    """
    return PoetryParser().parse(path)
