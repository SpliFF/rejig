"""Requirements.txt parser.

Parses requirements.txt files into PackageConfig objects.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rejig.packaging.models import Dependency, PackageConfig, PackageMetadata
from rejig.targets.base import Result

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class RequirementsParser:
    """Parser for requirements.txt files.

    Handles the full requirements.txt format including:
    - Simple packages: requests
    - Versioned packages: requests>=2.28.0
    - Packages with extras: requests[security]>=2.28.0
    - Environment markers: requests>=2.28.0; python_version>="3.10"
    - VCS URLs: git+https://github.com/user/repo.git@v1.0
    - Editable installs: -e ./local/package
    - Recursive includes: -r other-requirements.txt
    - Comments and blank lines (skipped)
    - Index options (skipped): -i, --index-url, --extra-index-url

    Parameters
    ----------
    rejig : Rejig | None
        Optional Rejig instance for resolving paths.

    Examples
    --------
    >>> parser = RequirementsParser()
    >>> config = parser.parse(Path("requirements.txt"))
    >>> for dep in config.dependencies:
    ...     print(dep.name, dep.version_spec)
    """

    def __init__(self, rejig: Rejig | None = None) -> None:
        self._rejig = rejig

    def parse(self, path: Path) -> PackageConfig:
        """Parse a requirements.txt file.

        Parameters
        ----------
        path : Path
            Path to the requirements.txt file.

        Returns
        -------
        PackageConfig
            Parsed package configuration with dependencies.
        """
        dependencies: list[Dependency] = []

        if path.exists():
            content = path.read_text()
            dependencies = self.parse_content(content, base_path=path.parent)

        return PackageConfig(
            format="requirements",
            source_path=path,
            metadata=PackageMetadata(),
            dependencies=dependencies,
        )

    def parse_content(
        self, content: str, base_path: Path | None = None
    ) -> list[Dependency]:
        """Parse requirements from content string.

        Parameters
        ----------
        content : str
            Content of a requirements.txt file.
        base_path : Path | None
            Base path for resolving relative includes.

        Returns
        -------
        list[Dependency]
            Parsed dependencies.
        """
        dependencies: list[Dependency] = []
        lines = content.splitlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            i += 1

            # Handle line continuations
            while line.endswith("\\") and i < len(lines):
                line = line[:-1] + lines[i].strip()
                i += 1

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Handle -r includes
            if line.startswith("-r ") or line.startswith("--requirement "):
                if line.startswith("-r "):
                    include_path = line[3:].strip()
                else:
                    include_path = line[14:].strip()

                if base_path:
                    include_file = base_path / include_path
                    if include_file.exists():
                        included_deps = self.parse(include_file).dependencies
                        dependencies.extend(included_deps)
                continue

            # Skip other options
            if line.startswith("-"):
                # -e is handled by Dependency.from_pip_line
                if not line.startswith("-e "):
                    continue

            # Parse the dependency
            dep = Dependency.from_pip_line(line)
            if dep:
                dependencies.append(dep)

        return dependencies

    def write(self, config: PackageConfig, path: Path, include_dev: bool = False) -> Result:
        """Write dependencies to a requirements.txt file.

        Parameters
        ----------
        config : PackageConfig
            Package configuration to write.
        path : Path
            Output path.
        include_dev : bool
            Whether to include dev dependencies.

        Returns
        -------
        Result
            Result of the operation.
        """
        lines: list[str] = []

        # Main dependencies
        for dep in sorted(config.dependencies, key=lambda d: d.name):
            lines.append(dep.to_pip_spec())

        # Dev dependencies (if requested)
        if include_dev and config.dev_dependencies:
            lines.append("")
            lines.append("# Development dependencies")
            for dep in sorted(config.dev_dependencies, key=lambda d: d.name):
                lines.append(dep.to_pip_spec())

        content = "\n".join(lines)
        if lines:
            content += "\n"

        try:
            path.write_text(content)
            return Result(
                success=True,
                message=f"Wrote {len(config.dependencies)} dependencies to {path}",
                files_changed=[path],
            )
        except Exception as e:
            return Result(
                success=False,
                message=f"Failed to write requirements: {e}",
            )


def parse_requirements(path: Path) -> PackageConfig:
    """Convenience function to parse a requirements.txt file.

    Parameters
    ----------
    path : Path
        Path to the requirements.txt file.

    Returns
    -------
    PackageConfig
        Parsed package configuration.
    """
    return RequirementsParser().parse(path)
