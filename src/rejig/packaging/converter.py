"""Package configuration converter.

Converts between different package manager formats.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rejig.packaging.models import Dependency, PackageConfig, PackageFormat, PackageMetadata
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


class PackageConfigConverter:
    """Convert between different package configuration formats.

    Supports conversion between:
    - requirements.txt
    - PEP 621 pyproject.toml
    - Poetry pyproject.toml
    - UV pyproject.toml

    Parameters
    ----------
    rejig : Rejig | None
        Optional Rejig instance.

    Examples
    --------
    >>> converter = PackageConfigConverter()
    >>> result = converter.poetry_to_pep621(Path("pyproject.toml"))
    >>> result = converter.to_requirements(config, Path("requirements.txt"))
    """

    def __init__(self, rejig: Rejig | None = None) -> None:
        self._rejig = rejig

    def to_requirements(
        self,
        config: PackageConfig,
        output: Path,
        include_dev: bool = False,
        dry_run: bool = False,
    ) -> Result:
        """Export configuration as requirements.txt.

        Parameters
        ----------
        config : PackageConfig
            Package configuration to export.
        output : Path
            Output file path.
        include_dev : bool
            Whether to include dev dependencies.
        dry_run : bool
            If True, don't write the file.

        Returns
        -------
        Result
            Result of the operation.
        """
        from rejig.packaging.requirements import RequirementsParser

        parser = RequirementsParser(self._rejig)

        if dry_run:
            deps = config.all_dependencies(include_dev=include_dev)
            return Result(
                success=True,
                message=f"[DRY RUN] Would write {len(deps)} dependencies to {output}",
                files_changed=[output],
            )

        return parser.write(config, output, include_dev=include_dev)

    def to_pep621(
        self,
        config: PackageConfig,
        output: Path,
        preserve_existing: bool = True,
        dry_run: bool = False,
    ) -> Result:
        """Export configuration as PEP 621 pyproject.toml.

        Parameters
        ----------
        config : PackageConfig
            Package configuration to export.
        output : Path
            Output file path.
        preserve_existing : bool
            If True and file exists, merge with existing config.
        dry_run : bool
            If True, don't write the file.

        Returns
        -------
        Result
            Result of the operation.
        """
        if tomli_w is None:
            return Result(
                success=False,
                message="tomli-w is required to write TOML files",
            )

        # Load existing data if preserving
        data: dict[str, Any] = {}
        if preserve_existing and output.exists() and tomllib:
            try:
                with open(output, "rb") as f:
                    data = tomllib.load(f)
            except Exception:
                pass

        # Build project section
        project = data.get("project", {})

        # Set metadata
        if config.metadata.name:
            project["name"] = config.metadata.name
        if config.metadata.version:
            project["version"] = config.metadata.version
        if config.metadata.description:
            project["description"] = config.metadata.description
        if config.metadata.python_requires:
            project["requires-python"] = config.metadata.python_requires
        if config.metadata.readme:
            project["readme"] = config.metadata.readme
        if config.metadata.license:
            project["license"] = {"text": config.metadata.license}
        if config.metadata.keywords:
            project["keywords"] = config.metadata.keywords
        if config.metadata.classifiers:
            project["classifiers"] = config.metadata.classifiers

        # Set authors
        if config.metadata.authors:
            authors = []
            for author in config.metadata.authors:
                if "<" in author and ">" in author:
                    # Parse "Name <email>" format
                    name = author.split("<")[0].strip()
                    email = author.split("<")[1].rstrip(">").strip()
                    authors.append({"name": name, "email": email})
                else:
                    authors.append({"name": author})
            project["authors"] = authors

        # Set URLs
        urls = project.get("urls", {})
        if config.metadata.homepage:
            urls["Homepage"] = config.metadata.homepage
        if config.metadata.repository:
            urls["Repository"] = config.metadata.repository
        if urls:
            project["urls"] = urls

        # Set dependencies
        if config.dependencies:
            project["dependencies"] = [dep.to_pep621_spec() for dep in config.dependencies]

        # Set optional dependencies
        if config.optional_dependencies or config.dev_dependencies:
            optional = project.get("optional-dependencies", {})
            for group, deps in config.optional_dependencies.items():
                optional[group] = [dep.to_pep621_spec() for dep in deps]
            if config.dev_dependencies:
                optional["dev"] = [dep.to_pep621_spec() for dep in config.dev_dependencies]
            project["optional-dependencies"] = optional

        # Set scripts
        if config.scripts:
            project["scripts"] = config.scripts

        data["project"] = project

        # Preserve tool config
        if config.tool_config:
            if "tool" not in data:
                data["tool"] = {}
            for tool_name, tool_data in config.tool_config.items():
                if tool_name not in data["tool"]:
                    data["tool"][tool_name] = tool_data

        if dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would write PEP 621 config to {output}",
                files_changed=[output],
            )

        try:
            with open(output, "wb") as f:
                tomli_w.dump(data, f)
            return Result(
                success=True,
                message=f"Wrote PEP 621 config to {output}",
                files_changed=[output],
            )
        except Exception as e:
            return Result(success=False, message=f"Failed to write TOML: {e}")

    def poetry_to_pep621(
        self, pyproject_path: Path, dry_run: bool = False
    ) -> Result:
        """Convert Poetry pyproject.toml to PEP 621 format in-place.

        This converts [tool.poetry] sections to [project] sections while
        preserving other tool configurations.

        Parameters
        ----------
        pyproject_path : Path
            Path to the pyproject.toml file.
        dry_run : bool
            If True, don't write changes.

        Returns
        -------
        Result
            Result of the operation.
        """
        from rejig.packaging.poetry import PoetryParser

        if tomllib is None or tomli_w is None:
            return Result(
                success=False,
                message="tomllib and tomli-w are required for conversion",
            )

        # Parse existing Poetry config
        parser = PoetryParser(self._rejig)
        config = parser.parse(pyproject_path)

        if config is None:
            return Result(
                success=False,
                message=f"Failed to parse Poetry config from {pyproject_path}",
            )

        # Load existing TOML to preserve non-poetry sections
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            return Result(success=False, message=f"Failed to read TOML: {e}")

        # Build new project section
        project: dict[str, Any] = {}

        if config.metadata.name:
            project["name"] = config.metadata.name
        if config.metadata.version:
            project["version"] = config.metadata.version
        if config.metadata.description:
            project["description"] = config.metadata.description
        if config.metadata.python_requires:
            project["requires-python"] = config.metadata.python_requires
        if config.metadata.readme:
            project["readme"] = config.metadata.readme
        if config.metadata.license:
            project["license"] = {"text": config.metadata.license}
        if config.metadata.keywords:
            project["keywords"] = config.metadata.keywords
        if config.metadata.classifiers:
            project["classifiers"] = config.metadata.classifiers

        # Authors
        if config.metadata.authors:
            authors = []
            for author in config.metadata.authors:
                if "<" in author and ">" in author:
                    name = author.split("<")[0].strip()
                    email = author.split("<")[1].rstrip(">").strip()
                    authors.append({"name": name, "email": email})
                else:
                    authors.append({"name": author})
            project["authors"] = authors

        # URLs
        urls = {}
        if config.metadata.homepage:
            urls["Homepage"] = config.metadata.homepage
        if config.metadata.repository:
            urls["Repository"] = config.metadata.repository
        if urls:
            project["urls"] = urls

        # Dependencies (convert Poetry version specs to PEP 440)
        if config.dependencies:
            project["dependencies"] = []
            for dep in config.dependencies:
                spec = self._poetry_dep_to_pep621(dep)
                project["dependencies"].append(spec)

        # Optional dependencies
        optional: dict[str, list[str]] = {}
        for group, deps in config.optional_dependencies.items():
            optional[group] = [self._poetry_dep_to_pep621(dep) for dep in deps]
        if config.dev_dependencies:
            dev_specs = [self._poetry_dep_to_pep621(dep) for dep in config.dev_dependencies]
            if "dev" in optional:
                optional["dev"].extend(dev_specs)
            else:
                optional["dev"] = dev_specs
        if optional:
            project["optional-dependencies"] = optional

        # Scripts
        if config.scripts:
            project["scripts"] = config.scripts

        # Update data
        data["project"] = project

        # Remove [tool.poetry] section
        if "tool" in data and "poetry" in data["tool"]:
            del data["tool"]["poetry"]

        if dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would convert {pyproject_path} from Poetry to PEP 621",
                files_changed=[pyproject_path],
            )

        try:
            with open(pyproject_path, "wb") as f:
                tomli_w.dump(data, f)
            return Result(
                success=True,
                message=f"Converted {pyproject_path} from Poetry to PEP 621",
                files_changed=[pyproject_path],
            )
        except Exception as e:
            return Result(success=False, message=f"Failed to write TOML: {e}")

    def _poetry_dep_to_pep621(self, dep: Dependency) -> str:
        """Convert a Poetry dependency to PEP 621 format."""
        # Convert Poetry version spec to PEP 440
        if dep.version_spec:
            version = self._poetry_version_to_pep440(dep.version_spec)
        else:
            version = None

        # Build PEP 621 spec
        spec = dep.name
        if dep.extras:
            spec += f"[{','.join(sorted(dep.extras))}]"
        if version:
            spec += version
        if dep.markers:
            spec += f"; {dep.markers}"

        return spec

    def _poetry_version_to_pep440(self, version: str) -> str:
        """Convert Poetry version constraint to PEP 440."""
        version = version.strip()

        # Handle caret (^) - compatible release
        if version.startswith("^"):
            base = version[1:]
            parts = base.split(".")
            if len(parts) >= 2:
                major = int(parts[0])
                if major == 0:
                    if len(parts) >= 2:
                        minor = int(parts[1])
                        return f">={base},<0.{minor + 1}.0"
                else:
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

        return version

    def requirements_to_pyproject(
        self,
        requirements_path: Path,
        pyproject_path: Path,
        format: PackageFormat = "pep621",
        name: str | None = None,
        version: str | None = None,
        dry_run: bool = False,
    ) -> Result:
        """Convert requirements.txt to pyproject.toml.

        Parameters
        ----------
        requirements_path : Path
            Path to requirements.txt.
        pyproject_path : Path
            Output pyproject.toml path.
        format : PackageFormat
            Target format ("pep621" or "poetry").
        name : str | None
            Package name (required if creating new pyproject.toml).
        version : str | None
            Package version.
        dry_run : bool
            If True, don't write changes.

        Returns
        -------
        Result
            Result of the operation.
        """
        from rejig.packaging.requirements import RequirementsParser

        # Parse requirements
        parser = RequirementsParser(self._rejig)
        config = parser.parse(requirements_path)

        # Set metadata
        config.metadata.name = name
        config.metadata.version = version

        if format == "pep621":
            return self.to_pep621(config, pyproject_path, dry_run=dry_run)
        else:
            return Result(
                success=False,
                message=f"Conversion to {format} not yet supported",
            )


def convert_poetry_to_pep621(pyproject_path: Path, dry_run: bool = False) -> Result:
    """Convenience function to convert Poetry to PEP 621.

    Parameters
    ----------
    pyproject_path : Path
        Path to pyproject.toml.
    dry_run : bool
        If True, don't write changes.

    Returns
    -------
    Result
        Result of the operation.
    """
    return PackageConfigConverter().poetry_to_pep621(pyproject_path, dry_run=dry_run)


def export_requirements(
    config: PackageConfig, output: Path, include_dev: bool = False
) -> Result:
    """Convenience function to export as requirements.txt.

    Parameters
    ----------
    config : PackageConfig
        Package configuration.
    output : Path
        Output file path.
    include_dev : bool
        Whether to include dev dependencies.

    Returns
    -------
    Result
        Result of the operation.
    """
    return PackageConfigConverter().to_requirements(config, output, include_dev=include_dev)
