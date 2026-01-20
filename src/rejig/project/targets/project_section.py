"""ProjectSectionTarget - Target for [project] section of pyproject.toml."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rejig.core.results import Result
from rejig.targets.config.toml import TomlTarget

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class ProjectSectionTarget(TomlTarget):
    """Target for the [project] section of pyproject.toml.

    Provides methods for managing project metadata.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : Path
        Path to pyproject.toml.

    Examples
    --------
    >>> project = pyproject.project()
    >>> project.name
    'myproject'
    >>> project.set_version("2.0.0")
    >>> project.set_python_requires(">=3.10")
    """

    def __init__(self, rejig: Rejig, path: Path) -> None:
        super().__init__(rejig, path)

    def __repr__(self) -> str:
        return f"ProjectSectionTarget({self.path})"

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def name(self) -> str | None:
        """Get the project name."""
        return self.get("project.name")

    @property
    def version(self) -> str | None:
        """Get the project version."""
        return self.get("project.version")

    @property
    def description(self) -> str | None:
        """Get the project description."""
        return self.get("project.description")

    @property
    def python_requires(self) -> str | None:
        """Get the Python version requirement."""
        return self.get("project.requires-python")

    @property
    def readme(self) -> str | None:
        """Get the README file path."""
        return self.get("project.readme")

    @property
    def license(self) -> str | dict | None:
        """Get the license."""
        return self.get("project.license")

    @property
    def authors(self) -> list[dict[str, str]]:
        """Get the list of authors."""
        return self.get("project.authors", [])

    @property
    def keywords(self) -> list[str]:
        """Get the keywords list."""
        return self.get("project.keywords", [])

    @property
    def classifiers(self) -> list[str]:
        """Get the PyPI classifiers."""
        return self.get("project.classifiers", [])

    # =========================================================================
    # Setters
    # =========================================================================

    def set_name(self, name: str) -> Result:
        """Set the project name.

        Parameters
        ----------
        name : str
            Project name.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set("project.name", name)

    def set_version(self, version: str) -> Result:
        """Set the project version.

        Parameters
        ----------
        version : str
            Version string.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> project.set_version("2.0.0")
        """
        return self.set("project.version", version)

    def set_description(self, description: str) -> Result:
        """Set the project description.

        Parameters
        ----------
        description : str
            Short description.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set("project.description", description)

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

        Examples
        --------
        >>> project.set_python_requires(">=3.10")
        """
        return self.set("project.requires-python", version_spec)

    def set_readme(self, readme: str) -> Result:
        """Set the README file path.

        Parameters
        ----------
        readme : str
            Path to README file.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set("project.readme", readme)

    def set_license(self, license: str) -> Result:
        """Set the license.

        Parameters
        ----------
        license : str
            License identifier (e.g., "MIT", "Apache-2.0").

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set("project.license", {"text": license})

    def set_keywords(self, keywords: list[str]) -> Result:
        """Set the keywords list.

        Parameters
        ----------
        keywords : list[str]
            List of keywords.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set("project.keywords", keywords)

    def add_keyword(self, keyword: str) -> Result:
        """Add a keyword.

        Parameters
        ----------
        keyword : str
            Keyword to add.

        Returns
        -------
        Result
            Result of the operation.
        """
        keywords = self.keywords
        if keyword not in keywords:
            keywords.append(keyword)
            return self.set("project.keywords", keywords)
        return Result(success=True, message="Keyword already exists")

    def set_classifiers(self, classifiers: list[str]) -> Result:
        """Set the PyPI classifiers.

        Parameters
        ----------
        classifiers : list[str]
            List of classifiers.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set("project.classifiers", classifiers)

    def add_classifier(self, classifier: str) -> Result:
        """Add a PyPI classifier.

        Parameters
        ----------
        classifier : str
            Classifier to add.

        Returns
        -------
        Result
            Result of the operation.
        """
        classifiers = self.classifiers
        if classifier not in classifiers:
            classifiers.append(classifier)
            return self.set("project.classifiers", classifiers)
        return Result(success=True, message="Classifier already exists")

    def set_authors(self, authors: list[dict[str, str] | str]) -> Result:
        """Set the authors list.

        Parameters
        ----------
        authors : list[dict | str]
            List of authors. Each can be:
            - A dict with "name" and optionally "email"
            - A string in "Name <email>" format

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> project.set_authors([
        ...     {"name": "John Doe", "email": "john@example.com"},
        ...     "Jane Doe <jane@example.com>"
        ... ])
        """
        parsed_authors = []
        for author in authors:
            if isinstance(author, dict):
                parsed_authors.append(author)
            elif "<" in author and ">" in author:
                name = author.split("<")[0].strip()
                email = author.split("<")[1].rstrip(">").strip()
                parsed_authors.append({"name": name, "email": email})
            else:
                parsed_authors.append({"name": author})

        return self.set("project.authors", parsed_authors)

    def add_author(self, name: str, email: str | None = None) -> Result:
        """Add an author.

        Parameters
        ----------
        name : str
            Author name.
        email : str | None
            Author email.

        Returns
        -------
        Result
            Result of the operation.
        """
        authors = self.authors
        author = {"name": name}
        if email:
            author["email"] = email
        authors.append(author)
        return self.set("project.authors", authors)

    # =========================================================================
    # URLs
    # =========================================================================

    @property
    def urls(self) -> dict[str, str]:
        """Get the project URLs."""
        return self.get("project.urls", {})

    def set_url(self, name: str, url: str) -> Result:
        """Set a project URL.

        Parameters
        ----------
        name : str
            URL name (e.g., "Homepage", "Repository", "Documentation").
        url : str
            URL value.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> project.set_url("Homepage", "https://example.com")
        >>> project.set_url("Repository", "https://github.com/user/repo")
        """
        urls = self.urls
        urls[name] = url
        return self.set("project.urls", urls)

    def set_homepage(self, url: str) -> Result:
        """Set the homepage URL."""
        return self.set_url("Homepage", url)

    def set_repository(self, url: str) -> Result:
        """Set the repository URL."""
        return self.set_url("Repository", url)

    def set_documentation(self, url: str) -> Result:
        """Set the documentation URL."""
        return self.set_url("Documentation", url)

    # =========================================================================
    # Version Operations
    # =========================================================================

    def bump_version(self, part: str = "patch") -> Result:
        """Bump the version number.

        Parameters
        ----------
        part : str
            Which part to bump: "major", "minor", or "patch".

        Returns
        -------
        Result
            Result with the new version in the message.

        Examples
        --------
        >>> project.bump_version("minor")  # 1.2.3 → 1.3.0
        """
        current = self.version
        if current is None:
            return self._operation_failed("bump_version", "Version not found")

        match = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", current)
        if not match:
            return self._operation_failed("bump_version", f"Cannot parse version: {current}")

        major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))

        if part == "major":
            major, minor, patch = major + 1, 0, 0
        elif part == "minor":
            minor, patch = minor + 1, 0
        elif part == "patch":
            patch += 1
        else:
            return self._operation_failed("bump_version", f"Invalid version part: {part}")

        new_version = f"{major}.{minor}.{patch}"
        result = self.set_version(new_version)

        if result.success:
            result.message = f"Bumped version from {current} to {new_version}"

        return result

    # =========================================================================
    # Metadata Dict
    # =========================================================================

    def get_metadata(self) -> dict[str, Any]:
        """Get all project metadata as a dictionary.

        Returns
        -------
        dict
            Dictionary with all metadata fields.
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "python_requires": self.python_requires,
            "readme": self.readme,
            "license": self.license,
            "authors": self.authors,
            "keywords": self.keywords,
            "classifiers": self.classifiers,
            "urls": self.urls,
        }

    def set_metadata(
        self,
        name: str | None = None,
        version: str | None = None,
        description: str | None = None,
        python_requires: str | None = None,
        readme: str | None = None,
        license: str | None = None,
        keywords: list[str] | None = None,
        authors: list[dict[str, str] | str] | None = None,
    ) -> Result:
        """Set multiple metadata fields at once.

        Parameters
        ----------
        name : str | None
            Project name.
        version : str | None
            Project version.
        description : str | None
            Project description.
        python_requires : str | None
            Python version requirement.
        readme : str | None
            README file path.
        license : str | None
            License identifier.
        keywords : list[str] | None
            Keywords list.
        authors : list | None
            Authors list.

        Returns
        -------
        Result
            Result of the operation.
        """
        data = self._load()
        if data is None:
            return self._operation_failed("set_metadata", "Failed to load pyproject.toml")

        if "project" not in data:
            data["project"] = {}

        project = data["project"]

        if name is not None:
            project["name"] = name
        if version is not None:
            project["version"] = version
        if description is not None:
            project["description"] = description
        if python_requires is not None:
            project["requires-python"] = python_requires
        if readme is not None:
            project["readme"] = readme
        if license is not None:
            project["license"] = {"text": license}
        if keywords is not None:
            project["keywords"] = keywords
        if authors is not None:
            parsed_authors = []
            for author in authors:
                if isinstance(author, dict):
                    parsed_authors.append(author)
                elif "<" in author and ">" in author:
                    n = author.split("<")[0].strip()
                    e = author.split("<")[1].rstrip(">").strip()
                    parsed_authors.append({"name": n, "email": e})
                else:
                    parsed_authors.append({"name": author})
            project["authors"] = parsed_authors

        return self._save(data)
