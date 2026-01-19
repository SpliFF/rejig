"""PEP 621 pyproject.toml parser.

Parses standard pyproject.toml files following PEP 621.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rejig.packaging.models import Dependency, PackageConfig, PackageMetadata
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


class PEP621Parser:
    """Parser for PEP 621 pyproject.toml files.

    Parses the standard [project] section of pyproject.toml as defined
    in PEP 621.

    Parameters
    ----------
    rejig : Rejig | None
        Optional Rejig instance.

    Examples
    --------
    >>> parser = PEP621Parser()
    >>> config = parser.parse(Path("pyproject.toml"))
    >>> print(config.metadata.name)
    myproject
    >>> for dep in config.dependencies:
    ...     print(dep.name, dep.version_spec)
    """

    def __init__(self, rejig: Rejig | None = None) -> None:
        self._rejig = rejig

    def parse(self, path: Path) -> PackageConfig | None:
        """Parse a PEP 621 pyproject.toml file.

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

        # Must have [project] section for PEP 621
        project = data.get("project")
        if not project:
            return None

        return self._parse_data(data, path)

    def _parse_data(self, data: dict[str, Any], path: Path) -> PackageConfig:
        """Parse loaded TOML data into PackageConfig."""
        project = data.get("project", {})

        # Parse metadata
        metadata = self._parse_metadata(project)

        # Parse dependencies
        dependencies = self._parse_dependencies(project.get("dependencies", []))

        # Parse optional dependencies (including dev)
        optional_deps: dict[str, list[Dependency]] = {}
        dev_dependencies: list[Dependency] = []

        for group, specs in project.get("optional-dependencies", {}).items():
            group_deps = self._parse_dependencies(specs)
            if group in ("dev", "development", "test", "testing"):
                dev_dependencies.extend(group_deps)
            optional_deps[group] = group_deps

        # Parse scripts
        scripts = {}
        if "scripts" in project:
            scripts = dict(project["scripts"])

        # Collect tool config
        tool_config = data.get("tool", {})

        return PackageConfig(
            format="pep621",
            source_path=path,
            metadata=metadata,
            dependencies=dependencies,
            dev_dependencies=dev_dependencies,
            optional_dependencies=optional_deps,
            scripts=scripts,
            tool_config=tool_config,
        )

    def _parse_metadata(self, project: dict[str, Any]) -> PackageMetadata:
        """Parse project metadata from [project] section."""
        authors: list[str] = []
        for author in project.get("authors", []):
            if isinstance(author, dict):
                name = author.get("name", "")
                email = author.get("email", "")
                if name and email:
                    authors.append(f"{name} <{email}>")
                elif name:
                    authors.append(name)
                elif email:
                    authors.append(email)
            else:
                authors.append(str(author))

        license_info = project.get("license")
        license_str = None
        if isinstance(license_info, dict):
            license_str = license_info.get("text") or license_info.get("file")
        elif isinstance(license_info, str):
            license_str = license_info

        return PackageMetadata(
            name=project.get("name"),
            version=project.get("version"),
            description=project.get("description"),
            authors=authors,
            license=license_str,
            python_requires=project.get("requires-python"),
            readme=project.get("readme"),
            homepage=project.get("urls", {}).get("Homepage"),
            repository=project.get("urls", {}).get("Repository"),
            keywords=project.get("keywords", []),
            classifiers=project.get("classifiers", []),
        )

    def _parse_dependencies(self, specs: list[str]) -> list[Dependency]:
        """Parse list of PEP 508 dependency specifications."""
        dependencies: list[Dependency] = []
        for spec in specs:
            dep = Dependency.from_pep621(spec)
            dependencies.append(dep)
        return dependencies

    def add_dependency(
        self,
        path: Path,
        name: str,
        version: str | None = None,
        dev: bool = False,
        group: str | None = None,
        dry_run: bool = False,
    ) -> Result:
        """Add a dependency to pyproject.toml.

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

        # Determine where to add
        if group:
            # Add to optional-dependencies group
            if "project" not in data:
                data["project"] = {}
            if "optional-dependencies" not in data["project"]:
                data["project"]["optional-dependencies"] = {}
            if group not in data["project"]["optional-dependencies"]:
                data["project"]["optional-dependencies"][group] = []

            deps_list = data["project"]["optional-dependencies"][group]
        elif dev:
            # Add to dev optional-dependencies
            if "project" not in data:
                data["project"] = {}
            if "optional-dependencies" not in data["project"]:
                data["project"]["optional-dependencies"] = {}
            if "dev" not in data["project"]["optional-dependencies"]:
                data["project"]["optional-dependencies"]["dev"] = []

            deps_list = data["project"]["optional-dependencies"]["dev"]
        else:
            # Add to main dependencies
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
        """Remove a dependency from pyproject.toml.

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

        # Check main dependencies
        if "project" in data and "dependencies" in data["project"]:
            new_deps = []
            for spec in data["project"]["dependencies"]:
                dep = Dependency.from_pep621(spec)
                if dep.name != normalized:
                    new_deps.append(spec)
                else:
                    found = True
            data["project"]["dependencies"] = new_deps

        # Check optional dependencies
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


def parse_pep621(path: Path) -> PackageConfig | None:
    """Convenience function to parse a PEP 621 pyproject.toml.

    Parameters
    ----------
    path : Path
        Path to pyproject.toml.

    Returns
    -------
    PackageConfig | None
        Parsed configuration, or None if parsing failed.
    """
    return PEP621Parser().parse(path)
