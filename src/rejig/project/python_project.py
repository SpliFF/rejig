"""PythonProject - High-level facade for Python project configuration.

This module provides a simplified facade that delegates to specialized
Target classes for each section of pyproject.toml.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from rejig.core.results import Result

if TYPE_CHECKING:
    from rejig.packaging.models import Dependency, PackageConfig
    from rejig.project.targets import (
        PyprojectTarget,
        ProjectSectionTarget,
        DependenciesTarget,
        ScriptsTarget,
        BlackConfigTarget,
        RuffConfigTarget,
        MypyConfigTarget,
        PytestConfigTarget,
        IsortConfigTarget,
        CoverageConfigTarget,
    )


class PythonProject:
    """High-level facade for Python project configuration.

    Provides convenient access to all pyproject.toml sections through
    specialized Target classes. Each section can be accessed either
    through convenience methods or by navigating to the section target.

    Parameters
    ----------
    path : str | Path
        Path to the project root directory.
    dry_run : bool
        If True, operations don't modify files.

    Examples
    --------
    >>> project = PythonProject("/path/to/project")
    >>>
    >>> # Access via convenience methods (delegates to targets)
    >>> project.add_dependency("requests", ">=2.28.0")
    >>> project.bump_version("minor")
    >>> project.configure_black(line_length=110)
    >>>
    >>> # Or access targets directly for more control
    >>> project.pyproject.dependencies().add("aiohttp", ">=3.8.0")
    >>> project.pyproject.black().set(target_version=["py310"])
    >>> project.pyproject.project().set_homepage("https://example.com")
    """

    def __init__(self, path: str | Path, dry_run: bool = False) -> None:
        self.path = Path(path).resolve()
        self.dry_run = dry_run
        self._pyproject: PyprojectTarget | None = None

    @property
    def pyproject_path(self) -> Path:
        """Path to pyproject.toml."""
        return self.path / "pyproject.toml"

    @property
    def exists(self) -> bool:
        """Check if pyproject.toml exists."""
        return self.pyproject_path.exists()

    # =========================================================================
    # Target Access
    # =========================================================================

    @property
    def pyproject(self) -> PyprojectTarget:
        """Get the PyprojectTarget for direct section navigation.

        Returns
        -------
        PyprojectTarget
            Target for pyproject.toml with navigation methods.

        Examples
        --------
        >>> project.pyproject.project().name
        'myproject'
        >>> project.pyproject.dependencies().add("requests")
        >>> project.pyproject.black().set(line_length=110)
        """
        if self._pyproject is None:
            from rejig.core.rejig import Rejig
            from rejig.project.targets import PyprojectTarget

            # Create a minimal Rejig instance for the target
            rj = Rejig(self.path, dry_run=self.dry_run)
            self._pyproject = PyprojectTarget(rj, self.pyproject_path)

        return self._pyproject

    def project(self) -> ProjectSectionTarget:
        """Navigate to the [project] section.

        Returns
        -------
        ProjectSectionTarget
            Target for project metadata.
        """
        return self.pyproject.project()

    def dependencies(self) -> DependenciesTarget:
        """Navigate to project.dependencies.

        Returns
        -------
        DependenciesTarget
            Target for main dependencies.
        """
        return self.pyproject.dependencies()

    def dev_dependencies(self) -> DependenciesTarget:
        """Navigate to project.optional-dependencies.dev.

        Returns
        -------
        DependenciesTarget
            Target for dev dependencies.
        """
        return self.pyproject.dev_dependencies()

    def scripts(self) -> ScriptsTarget:
        """Navigate to project.scripts.

        Returns
        -------
        ScriptsTarget
            Target for console scripts.
        """
        return self.pyproject.scripts()

    def black(self) -> BlackConfigTarget:
        """Navigate to [tool.black].

        Returns
        -------
        BlackConfigTarget
            Target for Black configuration.
        """
        return self.pyproject.black()

    def ruff(self) -> RuffConfigTarget:
        """Navigate to [tool.ruff].

        Returns
        -------
        RuffConfigTarget
            Target for Ruff configuration.
        """
        return self.pyproject.ruff()

    def mypy(self) -> MypyConfigTarget:
        """Navigate to [tool.mypy].

        Returns
        -------
        MypyConfigTarget
            Target for Mypy configuration.
        """
        return self.pyproject.mypy()

    def pytest(self) -> PytestConfigTarget:
        """Navigate to [tool.pytest].

        Returns
        -------
        PytestConfigTarget
            Target for pytest configuration.
        """
        return self.pyproject.pytest()

    def isort(self) -> IsortConfigTarget:
        """Navigate to [tool.isort].

        Returns
        -------
        IsortConfigTarget
            Target for isort configuration.
        """
        return self.pyproject.isort()

    def coverage(self) -> CoverageConfigTarget:
        """Navigate to [tool.coverage].

        Returns
        -------
        CoverageConfigTarget
            Target for coverage configuration.
        """
        return self.pyproject.coverage()

    # =========================================================================
    # Convenience Methods - Dependency Management
    # =========================================================================

    def add_dependency(
        self,
        name: str,
        version: str | None = None,
        extras: list[str] | None = None,
    ) -> Result:
        """Add a runtime dependency.

        Parameters
        ----------
        name : str
            Package name.
        version : str | None
            Version specification.
        extras : list[str] | None
            Optional extras.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> project.add_dependency("requests", ">=2.28.0")
        """
        return self.dependencies().add(name, version, extras)

    def add_dev_dependency(
        self,
        name: str,
        version: str | None = None,
        extras: list[str] | None = None,
    ) -> Result:
        """Add a development dependency.

        Parameters
        ----------
        name : str
            Package name.
        version : str | None
            Version specification.
        extras : list[str] | None
            Optional extras.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> project.add_dev_dependency("pytest", ">=7.0.0")
        """
        return self.dev_dependencies().add(name, version, extras)

    def add_optional_dependency(
        self,
        name: str,
        version: str | None = None,
        group: str = "optional",
        extras: list[str] | None = None,
    ) -> Result:
        """Add an optional dependency.

        Parameters
        ----------
        name : str
            Package name.
        version : str | None
            Version specification.
        group : str
            Dependency group name.
        extras : list[str] | None
            Optional extras.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> project.add_optional_dependency("redis", ">=4.0", group="cache")
        """
        return self.pyproject.optional_dependencies(group).add(name, version, extras)

    def remove_dependency(self, name: str) -> Result:
        """Remove a dependency from all sections.

        Parameters
        ----------
        name : str
            Package name.

        Returns
        -------
        Result
            Result of the operation.
        """
        # Try removing from main dependencies
        result = self.dependencies().remove(name)

        # Also try dev dependencies
        self.dev_dependencies().remove(name)

        return result

    def update_dependency(
        self,
        name: str,
        version: str,
        extras: list[str] | None = None,
    ) -> Result:
        """Update a dependency's version.

        Parameters
        ----------
        name : str
            Package name.
        version : str
            New version specification.
        extras : list[str] | None
            Optional extras.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.dependencies().update(name, version, extras)

    def list_dependencies(
        self, include_dev: bool = True, include_optional: bool = True
    ) -> list[str]:
        """List all dependencies.

        Parameters
        ----------
        include_dev : bool
            Include dev dependencies.
        include_optional : bool
            Include optional dependencies.

        Returns
        -------
        list[str]
            List of dependency specifications.
        """
        deps = self.dependencies().list()
        if include_dev:
            deps.extend(self.dev_dependencies().list())
        return deps

    def sync_dependencies_from_imports(self) -> Result:
        """Suggest missing dependencies based on imports.

        Returns
        -------
        Result
            Result with suggestions in `data` field.
        """
        return self.dependencies().sync_from_imports()

    # =========================================================================
    # Convenience Methods - Version Management
    # =========================================================================

    def get_version(self) -> str | None:
        """Get the project version.

        Returns
        -------
        str | None
            Version string, or None if not found.
        """
        return self.project().version

    def set_version(self, version: str) -> Result:
        """Set the project version.

        Parameters
        ----------
        version : str
            New version string.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.project().set_version(version)

    def bump_version(self, part: str = "patch") -> Result:
        """Bump the version number.

        Parameters
        ----------
        part : str
            Which part: "major", "minor", or "patch".

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.project().bump_version(part)

    def set_python_requires(self, version_spec: str) -> Result:
        """Set the Python version requirement.

        Parameters
        ----------
        version_spec : str
            Version specification (e.g., ">=3.10").

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.project().set_python_requires(version_spec)

    # =========================================================================
    # Convenience Methods - Scripts
    # =========================================================================

    def add_script(self, name: str, entry_point: str) -> Result:
        """Add a console script.

        Parameters
        ----------
        name : str
            Script name (command).
        entry_point : str
            Entry point (e.g., "package.module:function").

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.scripts().add(name, entry_point)

    def add_console_script(self, name: str, entry_point: str) -> Result:
        """Add a console script (alias for add_script).

        Parameters
        ----------
        name : str
            Script name.
        entry_point : str
            Entry point.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.add_script(name, entry_point)

    def remove_script(self, name: str) -> Result:
        """Remove a console script.

        Parameters
        ----------
        name : str
            Script name to remove.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.scripts().remove(name)

    def list_scripts(self) -> dict[str, str]:
        """List all console scripts.

        Returns
        -------
        dict[str, str]
            Mapping of script names to entry points.
        """
        return self.scripts().list()

    # =========================================================================
    # Convenience Methods - Tool Configuration
    # =========================================================================

    def configure_black(
        self,
        line_length: int | None = None,
        target_version: list[str] | None = None,
        skip_string_normalization: bool | None = None,
        extend_exclude: list[str] | None = None,
        **kwargs: Any,
    ) -> Result:
        """Configure Black formatter.

        Parameters
        ----------
        line_length : int | None
            Maximum line length.
        target_version : list[str] | None
            Target Python versions.
        skip_string_normalization : bool | None
            Skip string normalization.
        extend_exclude : list[str] | None
            Additional exclude patterns.
        **kwargs : Any
            Additional options.

        Returns
        -------
        Result
            Result of the operation.
        """
        options: dict[str, Any] = {}
        if line_length is not None:
            options["line_length"] = line_length
        if target_version is not None:
            options["target_version"] = target_version
        if skip_string_normalization is not None:
            options["skip_string_normalization"] = skip_string_normalization
        if extend_exclude is not None:
            options["extend_exclude"] = "\n".join(extend_exclude)
        options.update(kwargs)

        return self.black().set(**options)

    def configure_ruff(
        self,
        select: list[str] | None = None,
        ignore: list[str] | None = None,
        line_length: int | None = None,
        target_version: str | None = None,
        extend_exclude: list[str] | None = None,
        **kwargs: Any,
    ) -> Result:
        """Configure Ruff linter.

        Parameters
        ----------
        select : list[str] | None
            Rules to enable.
        ignore : list[str] | None
            Rules to ignore.
        line_length : int | None
            Maximum line length.
        target_version : str | None
            Target Python version.
        extend_exclude : list[str] | None
            Additional exclude patterns.
        **kwargs : Any
            Additional options.

        Returns
        -------
        Result
            Result of the operation.
        """
        ruff = self.ruff()
        if line_length is not None:
            ruff.set_line_length(line_length)
        if target_version is not None:
            ruff.set_target_version(target_version)
        if select is not None:
            ruff.select(select)
        if ignore is not None:
            ruff.ignore(ignore)
        if extend_exclude is not None:
            ruff.set_extend_exclude(extend_exclude)
        if kwargs:
            return ruff.set(**kwargs)
        return Result(success=True, message="Configured Ruff")

    def configure_mypy(
        self,
        strict: bool | None = None,
        ignore_missing_imports: bool | None = None,
        python_version: str | None = None,
        warn_return_any: bool | None = None,
        warn_unused_configs: bool | None = None,
        **kwargs: Any,
    ) -> Result:
        """Configure Mypy type checker.

        Parameters
        ----------
        strict : bool | None
            Enable strict mode.
        ignore_missing_imports : bool | None
            Ignore missing imports.
        python_version : str | None
            Python version.
        warn_return_any : bool | None
            Warn about returning Any.
        warn_unused_configs : bool | None
            Warn about unused config.
        **kwargs : Any
            Additional options.

        Returns
        -------
        Result
            Result of the operation.
        """
        options: dict[str, Any] = {}
        if strict is not None:
            options["strict"] = strict
        if ignore_missing_imports is not None:
            options["ignore_missing_imports"] = ignore_missing_imports
        if python_version is not None:
            options["python_version"] = python_version
        if warn_return_any is not None:
            options["warn_return_any"] = warn_return_any
        if warn_unused_configs is not None:
            options["warn_unused_configs"] = warn_unused_configs
        options.update(kwargs)

        return self.mypy().set(**options)

    def configure_pytest(
        self,
        testpaths: list[str] | None = None,
        addopts: str | None = None,
        python_files: list[str] | None = None,
        python_classes: list[str] | None = None,
        python_functions: list[str] | None = None,
        **kwargs: Any,
    ) -> Result:
        """Configure pytest.

        Parameters
        ----------
        testpaths : list[str] | None
            Test directories.
        addopts : str | None
            Additional options.
        python_files : list[str] | None
            File patterns.
        python_classes : list[str] | None
            Class patterns.
        python_functions : list[str] | None
            Function patterns.
        **kwargs : Any
            Additional options.

        Returns
        -------
        Result
            Result of the operation.
        """
        pt = self.pytest()
        if testpaths is not None:
            pt.set_testpaths(testpaths)
        if addopts is not None:
            pt.set_addopts(addopts)
        if python_files is not None:
            pt.set_python_files(python_files)
        if python_classes is not None:
            pt.set_python_classes(python_classes)
        if python_functions is not None:
            pt.set_python_functions(python_functions)
        if kwargs:
            return pt.set(**kwargs)
        return Result(success=True, message="Configured pytest")

    def configure_isort(
        self,
        profile: str | None = None,
        line_length: int | None = None,
        known_first_party: list[str] | None = None,
        known_third_party: list[str] | None = None,
        skip: list[str] | None = None,
        **kwargs: Any,
    ) -> Result:
        """Configure isort.

        Parameters
        ----------
        profile : str | None
            isort profile (e.g., "black").
        line_length : int | None
            Maximum line length.
        known_first_party : list[str] | None
            First-party packages.
        known_third_party : list[str] | None
            Third-party packages.
        skip : list[str] | None
            Paths to skip.
        **kwargs : Any
            Additional options.

        Returns
        -------
        Result
            Result of the operation.
        """
        isort = self.isort()
        if profile is not None:
            isort.set_profile(profile)
        if line_length is not None:
            isort.set_line_length(line_length)
        if known_first_party is not None:
            isort.set_known_first_party(known_first_party)
        if known_third_party is not None:
            isort.set_known_third_party(known_third_party)
        if skip is not None:
            isort.set_skip(skip)
        if kwargs:
            return isort.set(**kwargs)
        return Result(success=True, message="Configured isort")

    def get_tool_config(self, tool_name: str) -> dict[str, Any]:
        """Get configuration for a tool.

        Parameters
        ----------
        tool_name : str
            Tool name.

        Returns
        -------
        dict
            Tool configuration.
        """
        return self.pyproject.tool(tool_name).get_config()

    def set_tool_config(self, tool_name: str, config: dict[str, Any]) -> Result:
        """Set configuration for a tool.

        Parameters
        ----------
        tool_name : str
            Tool name.
        config : dict
            Configuration to set.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.pyproject.tool(tool_name).set_config(config)

    # =========================================================================
    # Format Conversion
    # =========================================================================

    def convert_setup_py_to_pyproject(self) -> Result:
        """Convert setup.py to pyproject.toml.

        Returns
        -------
        Result
            Result of the operation.
        """
        import re

        setup_py = self.path / "setup.py"
        if not setup_py.exists():
            return Result(success=False, message="setup.py not found")

        try:
            content = setup_py.read_text()

            # Extract common fields
            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            description_match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
            python_requires_match = re.search(r'python_requires\s*=\s*["\']([^"\']+)["\']', content)

            name = name_match.group(1) if name_match else "unknown"
            version = version_match.group(1) if version_match else "0.1.0"
            description = description_match.group(1) if description_match else None
            python_requires = python_requires_match.group(1) if python_requires_match else ">=3.10"

            return self.pyproject.init(name, version, description, python_requires)

        except Exception as e:
            return Result(success=False, message=f"Failed to parse setup.py: {e}")

    def convert_requirements_to_pyproject(
        self, requirements_path: Path | str | None = None
    ) -> Result:
        """Convert requirements.txt to pyproject.toml dependencies.

        Parameters
        ----------
        requirements_path : Path | str | None
            Path to requirements.txt.

        Returns
        -------
        Result
            Result of the operation.
        """
        from rejig.packaging.converter import PackageConfigConverter

        if requirements_path is None:
            requirements_path = self.path / "requirements.txt"
        else:
            requirements_path = Path(requirements_path)
            if not requirements_path.is_absolute():
                requirements_path = self.path / requirements_path

        if not requirements_path.exists():
            return Result(success=False, message=f"Requirements file not found: {requirements_path}")

        converter = PackageConfigConverter()
        return converter.requirements_to_pyproject(
            requirements_path,
            self.pyproject_path,
            dry_run=self.dry_run,
        )

    def export_requirements(
        self,
        output: Path | str | None = None,
        include_dev: bool = False,
    ) -> Result:
        """Export dependencies as requirements.txt.

        Parameters
        ----------
        output : Path | str | None
            Output path.
        include_dev : bool
            Include dev dependencies.

        Returns
        -------
        Result
            Result of the operation.
        """
        from rejig.packaging.converter import PackageConfigConverter

        config = self.get_package_config()
        if config is None:
            return Result(success=False, message="No package configuration found")

        if output is None:
            output = self.path / "requirements.txt"
        else:
            output = Path(output)
            if not output.is_absolute():
                output = self.path / output

        converter = PackageConfigConverter()
        return converter.to_requirements(config, output, include_dev=include_dev, dry_run=self.dry_run)

    # =========================================================================
    # Project Metadata
    # =========================================================================

    def get_package_config(self) -> PackageConfig | None:
        """Get the parsed package configuration.

        Returns
        -------
        PackageConfig | None
            Parsed config, or None if not found.
        """
        from rejig.packaging.detector import get_package_config

        return get_package_config(self.path)

    def get_format(self) -> str | None:
        """Detect the pyproject.toml format.

        Returns
        -------
        str | None
            "pep621", "poetry", "uv", or None.
        """
        return self.pyproject.get_format()

    def get_metadata(self) -> dict[str, Any]:
        """Get all project metadata.

        Returns
        -------
        dict
            Project metadata.
        """
        return self.project().get_metadata()

    def set_metadata(
        self,
        name: str | None = None,
        description: str | None = None,
        authors: list[str] | None = None,
        license: str | None = None,
        readme: str | None = None,
        homepage: str | None = None,
        repository: str | None = None,
        keywords: list[str] | None = None,
    ) -> Result:
        """Set project metadata fields.

        Parameters
        ----------
        name : str | None
            Project name.
        description : str | None
            Description.
        authors : list[str] | None
            Authors.
        license : str | None
            License.
        readme : str | None
            README path.
        homepage : str | None
            Homepage URL.
        repository : str | None
            Repository URL.
        keywords : list[str] | None
            Keywords.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.project().set_metadata(
            name=name,
            version=None,
            description=description,
            python_requires=None,
            readme=readme,
            license=license,
            keywords=keywords,
            authors=authors,
        )

    # =========================================================================
    # Initialization
    # =========================================================================

    def init(
        self,
        name: str,
        version: str = "0.1.0",
        description: str | None = None,
        python_requires: str = ">=3.10",
    ) -> Result:
        """Initialize a new pyproject.toml.

        Parameters
        ----------
        name : str
            Project name.
        version : str
            Initial version.
        description : str | None
            Project description.
        python_requires : str
            Python version requirement.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.pyproject.init(name, version, description, python_requires)
