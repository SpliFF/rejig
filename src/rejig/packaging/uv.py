"""UV pyproject.toml parser.

Parses UV-specific pyproject.toml configuration.
UV uses PEP 621 standard with extensions in [tool.uv].
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rejig.packaging.models import Dependency, PackageConfig, PackageMetadata
from rejig.packaging.pep621 import PEP621Parser
from rejig.targets.base import Result

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


class UVParser:
    """Parser for UV pyproject.toml files.

    UV uses standard PEP 621 format with UV-specific extensions in [tool.uv]:
    - dev-dependencies: Development dependencies
    - sources: Custom package sources
    - index: Index configuration
    - override-dependencies: Dependency overrides

    Parameters
    ----------
    rejig : Rejig | None
        Optional Rejig instance.

    Examples
    --------
    >>> parser = UVParser()
    >>> config = parser.parse(Path("pyproject.toml"))
    >>> print(config.metadata.name)
    myproject
    """

    def __init__(self, rejig: Rejig | None = None) -> None:
        self._rejig = rejig
        self._pep621_parser = PEP621Parser(rejig)

    def parse(self, path: Path) -> PackageConfig | None:
        """Parse a UV pyproject.toml file.

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

        # Must have [tool.uv] section to be considered UV format
        uv_config = data.get("tool", {}).get("uv")
        if uv_config is None:
            return None

        # Parse as PEP 621 first
        config = self._pep621_parser.parse(path)
        if config is None:
            return None

        # Override format to UV
        config.format = "uv"  # type: ignore

        # Parse UV-specific dev dependencies
        dev_deps = uv_config.get("dev-dependencies", [])
        for spec in dev_deps:
            dep = Dependency.from_pep621(spec)
            dep.group = "dev"
            config.dev_dependencies.append(dep)

        # Store UV config in tool_config
        config.tool_config["uv"] = uv_config

        return config

    def add_dependency(
        self,
        path: Path,
        name: str,
        version: str | None = None,
        dev: bool = False,
        group: str | None = None,
        dry_run: bool = False,
    ) -> Result:
        """Add a dependency to UV pyproject.toml.

        Parameters
        ----------
        path : Path
            Path to pyproject.toml.
        name : str
            Package name.
        version : str | None
            Version specification.
        dev : bool
            Whether this is a dev dependency.
        group : str | None
            Optional dependency group name.
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

        # Build dependency spec
        dep = Dependency(name=name, version_spec=version)
        spec = dep.to_pep621_spec()

        if dev:
            # Add to [tool.uv.dev-dependencies]
            if "tool" not in data:
                data["tool"] = {}
            if "uv" not in data["tool"]:
                data["tool"]["uv"] = {}
            if "dev-dependencies" not in data["tool"]["uv"]:
                data["tool"]["uv"]["dev-dependencies"] = []

            deps_list = data["tool"]["uv"]["dev-dependencies"]
        elif group:
            # Add to optional-dependencies group (standard PEP 621)
            if "project" not in data:
                data["project"] = {}
            if "optional-dependencies" not in data["project"]:
                data["project"]["optional-dependencies"] = {}
            if group not in data["project"]["optional-dependencies"]:
                data["project"]["optional-dependencies"][group] = []

            deps_list = data["project"]["optional-dependencies"][group]
        else:
            # Add to main dependencies (standard PEP 621)
            if "project" not in data:
                data["project"] = {}
            if "dependencies" not in data["project"]:
                data["project"]["dependencies"] = []

            deps_list = data["project"]["dependencies"]

        # Check if already exists
        normalized = Dependency._normalize_name(name)
        for existing in deps_list:
            existing_dep = Dependency.from_pep621(existing)
            if existing_dep.name == normalized:
                return Result(success=True, message=f"Dependency {name} already exists")

        deps_list.append(spec)

        if dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add {spec} to {path}",
                files_changed=[path],
            )

        try:
            with open(path, "wb") as f:
                tomli_w.dump(data, f)
            return Result(
                success=True,
                message=f"Added {spec} to {path}",
                files_changed=[path],
            )
        except Exception as e:
            return Result(success=False, message=f"Failed to write TOML: {e}")

    def remove_dependency(
        self, path: Path, name: str, dry_run: bool = False
    ) -> Result:
        """Remove a dependency from UV pyproject.toml.

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

        normalized = Dependency._normalize_name(name)
        found = False

        # Check [project.dependencies]
        if "project" in data and "dependencies" in data["project"]:
            new_deps = []
            for spec in data["project"]["dependencies"]:
                dep = Dependency.from_pep621(spec)
                if dep.name != normalized:
                    new_deps.append(spec)
                else:
                    found = True
            data["project"]["dependencies"] = new_deps

        # Check [project.optional-dependencies]
        if "project" in data and "optional-dependencies" in data["project"]:
            for group in data["project"]["optional-dependencies"]:
                new_deps = []
                for spec in data["project"]["optional-dependencies"][group]:
                    dep = Dependency.from_pep621(spec)
                    if dep.name != normalized:
                        new_deps.append(spec)
                    else:
                        found = True
                data["project"]["optional-dependencies"][group] = new_deps

        # Check [tool.uv.dev-dependencies]
        if "tool" in data and "uv" in data["tool"]:
            if "dev-dependencies" in data["tool"]["uv"]:
                new_deps = []
                for spec in data["tool"]["uv"]["dev-dependencies"]:
                    dep = Dependency.from_pep621(spec)
                    if dep.name != normalized:
                        new_deps.append(spec)
                    else:
                        found = True
                data["tool"]["uv"]["dev-dependencies"] = new_deps

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


def parse_uv(path: Path) -> PackageConfig | None:
    """Convenience function to parse a UV pyproject.toml.

    Parameters
    ----------
    path : Path
        Path to pyproject.toml.

    Returns
    -------
    PackageConfig | None
        Parsed configuration, or None if parsing failed.
    """
    return UVParser().parse(path)
