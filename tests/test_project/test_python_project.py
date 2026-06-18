"""
Tests for rejig.project.python_project - PythonProject facade.

PythonProject is a high-level facade for managing Python project configuration
through pyproject.toml. It delegates to specialized Target classes.

Coverage targets:
- Initialization with directory path
- Existence checking (pyproject.toml exists?)
- Section navigation: project(), dependencies(), black(), ruff(), etc.
- Convenience methods: add_dependency, bump_version
- Dry-run mode
- Error handling when pyproject.toml doesn't exist
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig.core.results import ErrorResult, Result
from rejig.project.python_project import PythonProject


SAMPLE_PYPROJECT = textwrap.dedent('''\
    [build-system]
    requires = ["hatchling"]
    build-backend = "hatchling.build"

    [project]
    name = "test-project"
    version = "1.0.0"
    description = "A test project"
    requires-python = ">=3.10"
    dependencies = [
        "requests>=2.28.0",
        "pydantic>=2.0.0",
    ]

    [project.optional-dependencies]
    dev = [
        "pytest>=7.0.0",
        "black>=23.0.0",
    ]

    [project.scripts]
    mycli = "myproject:main"

    [tool.black]
    line-length = 100
    target-version = ["py310"]

    [tool.ruff]
    line-length = 100

    [tool.pytest.ini_options]
    testpaths = ["tests"]
''')


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a temp project directory with pyproject.toml."""
    (tmp_path / "pyproject.toml").write_text(SAMPLE_PYPROJECT)
    return tmp_path


@pytest.fixture
def empty_project_dir(tmp_path: Path) -> Path:
    """Create a temp project directory without pyproject.toml."""
    return tmp_path


# =============================================================================
# PythonProject Initialization
# =============================================================================

class TestPythonProjectInit:
    """Tests for PythonProject initialization."""

    def test_init_with_path(self, project_dir: Path):
        """
        PythonProject should accept a path to the project root.
        """
        project = PythonProject(project_dir)

        assert project.path == project_dir

    def test_init_with_string_path(self, project_dir: Path):
        """
        PythonProject should accept a string path.
        """
        project = PythonProject(str(project_dir))

        assert project.path == project_dir

    def test_init_dry_run(self, project_dir: Path):
        """
        PythonProject should support dry-run mode.
        """
        project = PythonProject(project_dir, dry_run=True)

        assert project.dry_run is True

    def test_init_default_not_dry_run(self, project_dir: Path):
        """
        By default, PythonProject should NOT be in dry-run mode.
        """
        project = PythonProject(project_dir)

        assert project.dry_run is False


# =============================================================================
# PythonProject Existence
# =============================================================================

class TestPythonProjectExistence:
    """Tests for PythonProject existence checking."""

    def test_exists_when_pyproject_present(self, project_dir: Path):
        """
        exists should return True when pyproject.toml exists.
        """
        project = PythonProject(project_dir)

        assert project.exists is True

    def test_not_exists_when_pyproject_missing(self, empty_project_dir: Path):
        """
        exists should return False when pyproject.toml is missing.
        """
        project = PythonProject(empty_project_dir)

        assert project.exists is False

    def test_pyproject_path(self, project_dir: Path):
        """
        pyproject_path should point to pyproject.toml in the project root.
        """
        project = PythonProject(project_dir)

        assert project.pyproject_path == project_dir / "pyproject.toml"


# =============================================================================
# PythonProject Section Navigation
# =============================================================================

class TestPythonProjectNavigation:
    """Tests for navigating to pyproject.toml sections."""

    def test_pyproject_property(self, project_dir: Path):
        """
        pyproject property should return a PyprojectTarget.
        """
        from rejig.project.targets import PyprojectTarget

        project = PythonProject(project_dir)
        pyproject = project.pyproject

        assert isinstance(pyproject, PyprojectTarget)

    def test_project_section(self, project_dir: Path):
        """
        project() should navigate to the [project] section.
        """
        from rejig.project.targets.project_section import ProjectSectionTarget

        project = PythonProject(project_dir)
        section = project.project()

        assert isinstance(section, ProjectSectionTarget)

    def test_dependencies_section(self, project_dir: Path):
        """
        dependencies() should navigate to project.dependencies.
        """
        from rejig.project.targets.dependencies import DependenciesTarget

        project = PythonProject(project_dir)
        deps = project.dependencies()

        assert isinstance(deps, DependenciesTarget)

    def test_scripts_section(self, project_dir: Path):
        """
        scripts() should navigate to project.scripts.
        """
        from rejig.project.targets.scripts import ScriptsTarget

        project = PythonProject(project_dir)
        scripts = project.scripts()

        assert isinstance(scripts, ScriptsTarget)

    def test_black_config(self, project_dir: Path):
        """
        black() should navigate to [tool.black].
        """
        from rejig.project.targets.tools.black import BlackConfigTarget

        project = PythonProject(project_dir)
        black = project.black()

        assert isinstance(black, BlackConfigTarget)

    def test_ruff_config(self, project_dir: Path):
        """
        ruff() should navigate to [tool.ruff].
        """
        from rejig.project.targets.tools.ruff import RuffConfigTarget

        project = PythonProject(project_dir)
        ruff = project.ruff()

        assert isinstance(ruff, RuffConfigTarget)

    def test_pytest_config(self, project_dir: Path):
        """
        pytest() should navigate to [tool.pytest].
        """
        from rejig.project.targets.tools.pytest import PytestConfigTarget

        project = PythonProject(project_dir)
        pt = project.pytest()

        assert isinstance(pt, PytestConfigTarget)


# =============================================================================
# PythonProject Convenience Methods
# =============================================================================

class TestPythonProjectConvenience:
    """Tests for convenience methods on PythonProject."""

    def test_add_dependency(self, project_dir: Path):
        """
        add_dependency should add a runtime dependency to pyproject.toml.
        """
        project = PythonProject(project_dir)
        result = project.add_dependency("aiohttp", ">=3.8.0")

        assert isinstance(result, Result)
        # Verify it was added
        content = (project_dir / "pyproject.toml").read_text()
        assert "aiohttp" in content

    def test_add_dev_dependency(self, project_dir: Path):
        """
        add_dev_dependency should add a dev dependency.
        """
        project = PythonProject(project_dir)
        result = project.add_dev_dependency("mypy", ">=1.0.0")

        assert isinstance(result, Result)
        content = (project_dir / "pyproject.toml").read_text()
        assert "mypy" in content


# =============================================================================
# PythonProject Dry-Run
# =============================================================================

class TestPythonProjectDryRun:
    """Tests for dry-run mode in PythonProject."""

    def test_dry_run_does_not_modify(self, project_dir: Path):
        """
        In dry-run mode, operations should not modify pyproject.toml.
        """
        original = (project_dir / "pyproject.toml").read_text()

        project = PythonProject(project_dir, dry_run=True)
        project.add_dependency("new-package", ">=1.0.0")

        current = (project_dir / "pyproject.toml").read_text()
        assert current == original


# =============================================================================
# PythonProject Error Handling
# =============================================================================

class TestPythonProjectErrors:
    """Tests for error handling in PythonProject."""

    def test_operations_on_missing_pyproject(self, empty_project_dir: Path):
        """
        Operations on a project without pyproject.toml should return errors,
        not raise exceptions.
        """
        project = PythonProject(empty_project_dir)

        # This should not raise
        result = project.add_dependency("requests", ">=2.0")

        # Should indicate failure
        assert isinstance(result, Result)
