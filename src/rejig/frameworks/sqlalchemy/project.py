"""SQLAlchemy project class for refactoring operations.

This module provides the main SQLAlchemyProject class that combines all
SQLAlchemy-specific refactoring capabilities.
"""
from __future__ import annotations

import re
from pathlib import Path

from rejig.core import Rejig
from rejig.core.results import Result

from .models import ModelManager
from .relationships import RelationshipManager


class SQLAlchemyProject:
    """
    Represents a SQLAlchemy project for refactoring operations.

    This is the main entry point for SQLAlchemy-specific refactoring operations.
    Initialize with the path to your project directory containing SQLAlchemy models.

    Parameters
    ----------
    project_root : Path | str
        Path to the project root directory.
    models_path : str | Path | None, optional
        Path to models directory or file. If None, searches for common patterns.
    dry_run : bool, optional
        If True, all operations will report what they would do without making
        actual changes. Defaults to False.

    Attributes
    ----------
    project_root : Path
        Resolved absolute path to the project root directory.
    models_path : Path
        Path to the SQLAlchemy models.
    dry_run : bool
        Whether operations are in dry-run mode.

    Examples
    --------
    >>> sqla = SQLAlchemyProject("/path/to/myproject")
    >>> sqla.add_column("User", "email", "String(255)", nullable=False)
    Result(success=True, ...)

    >>> # Preview changes without modifying files
    >>> sqla = SQLAlchemyProject("/path/to/myproject", dry_run=True)
    >>> result = sqla.add_relationship("User", "posts", "Post", back_populates="author")
    >>> print(result.message)
    [DRY RUN] Would add relationship 'posts' to 'User'
    """

    def __init__(
        self,
        project_root: Path | str,
        models_path: str | Path | None = None,
        dry_run: bool = False,
    ):
        self.project_root = Path(project_root).resolve()
        self.dry_run = dry_run

        if not self.project_root.exists():
            raise ValueError(f"Project root directory not found: {self.project_root}")

        # Determine models path
        self.models_path = self._find_models_path(models_path)

        # Initialize sub-managers
        self._models = ModelManager(self)
        self._relationships = RelationshipManager(self)

        # Create internal Rejig instance for CST operations
        self._rejig = Rejig(self.project_root, dry_run=dry_run)

    def _find_models_path(self, models_path: str | Path | None) -> Path:
        """Find the SQLAlchemy models path."""
        if models_path:
            path = Path(models_path)
            if not path.is_absolute():
                path = self.project_root / path
            return path

        # Search for common patterns
        candidates = [
            self.project_root / "models",
            self.project_root / "app" / "models",
            self.project_root / "src" / "models",
            self.project_root / "models.py",
            self.project_root / "app" / "models.py",
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        # Default to models directory
        return self.project_root / "models"

    def close(self) -> None:
        """Close the project and clean up resources."""
        self._rejig.close()

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up on context exit."""
        self.close()
        return False

    # -------------------------------------------------------------------------
    # Model Discovery Methods
    # -------------------------------------------------------------------------

    def find_model(self, model_name: str) -> Path | None:
        """
        Find the file containing a SQLAlchemy model.

        Parameters
        ----------
        model_name : str
            Name of the model class to find.

        Returns
        -------
        Path | None
            Path to file containing the model, or None if not found.
        """
        return self._models.find_model(model_name)

    def list_models(self) -> list[dict[str, str]]:
        """
        List all SQLAlchemy models in the project.

        Returns
        -------
        list[dict[str, str]]
            List of dicts with 'name', 'tablename', and 'file' keys.
        """
        return self._models.list_models()

    def get_model_columns(self, model_name: str) -> list[dict[str, str]]:
        """
        Get all columns for a model.

        Parameters
        ----------
        model_name : str
            Name of the model class.

        Returns
        -------
        list[dict[str, str]]
            List of dicts with 'name', 'type', 'nullable', 'primary_key' keys.
        """
        return self._models.get_model_columns(model_name)

    def get_model_relationships(self, model_name: str) -> list[dict[str, str]]:
        """
        Get all relationships for a model.

        Parameters
        ----------
        model_name : str
            Name of the model class.

        Returns
        -------
        list[dict[str, str]]
            List of dicts with 'name', 'target', 'back_populates' keys.
        """
        return self._relationships.get_model_relationships(model_name)

    # -------------------------------------------------------------------------
    # Column Management (delegated to ModelManager)
    # -------------------------------------------------------------------------

    def add_column(
        self,
        model_name: str,
        column_name: str,
        column_type: str,
        nullable: bool = True,
        default: str | None = None,
        primary_key: bool = False,
        unique: bool = False,
        index: bool = False,
        foreign_key: str | None = None,
    ) -> Result:
        """
        Add a column to a SQLAlchemy model.

        Parameters
        ----------
        model_name : str
            Name of the model class.
        column_name : str
            Name of the new column.
        column_type : str
            SQLAlchemy type (e.g., 'String(255)', 'Integer', 'DateTime').
        nullable : bool
            Whether the column allows NULL values.
        default : str | None
            Default value expression.
        primary_key : bool
            Whether this is a primary key column.
        unique : bool
            Whether values must be unique.
        index : bool
            Whether to create an index on this column.
        foreign_key : str | None
            Foreign key reference (e.g., 'users.id').

        Returns
        -------
        Result
            Result with success status.
        """
        return self._models.add_column(
            model_name, column_name, column_type, nullable, default,
            primary_key, unique, index, foreign_key
        )

    def remove_column(
        self,
        model_name: str,
        column_name: str,
    ) -> Result:
        """
        Remove a column from a SQLAlchemy model.

        Parameters
        ----------
        model_name : str
            Name of the model class.
        column_name : str
            Name of the column to remove.

        Returns
        -------
        Result
            Result with success status.
        """
        return self._models.remove_column(model_name, column_name)

    def rename_column(
        self,
        model_name: str,
        old_name: str,
        new_name: str,
    ) -> Result:
        """
        Rename a column in a SQLAlchemy model.

        Parameters
        ----------
        model_name : str
            Name of the model class.
        old_name : str
            Current column name.
        new_name : str
            New column name.

        Returns
        -------
        Result
            Result with success status.
        """
        return self._models.rename_column(model_name, old_name, new_name)

    # -------------------------------------------------------------------------
    # Relationship Management (delegated to RelationshipManager)
    # -------------------------------------------------------------------------

    def add_relationship(
        self,
        model_name: str,
        relationship_name: str,
        target_model: str,
        back_populates: str | None = None,
        backref: str | None = None,
        lazy: str = "select",
        uselist: bool | None = None,
        foreign_keys: str | None = None,
    ) -> Result:
        """
        Add a relationship to a SQLAlchemy model.

        Parameters
        ----------
        model_name : str
            Name of the model class.
        relationship_name : str
            Name of the relationship attribute.
        target_model : str
            Target model class name.
        back_populates : str | None
            Attribute name on target for bidirectional relationship.
        backref : str | None
            Alternative to back_populates for auto-generated reverse.
        lazy : str
            Loading strategy ('select', 'joined', 'subquery', 'dynamic').
        uselist : bool | None
            If False, relationship is scalar (one-to-one).
        foreign_keys : str | None
            Explicit foreign key column(s).

        Returns
        -------
        Result
            Result with success status.
        """
        return self._relationships.add_relationship(
            model_name, relationship_name, target_model, back_populates,
            backref, lazy, uselist, foreign_keys
        )

    def remove_relationship(
        self,
        model_name: str,
        relationship_name: str,
    ) -> Result:
        """
        Remove a relationship from a SQLAlchemy model.

        Parameters
        ----------
        model_name : str
            Name of the model class.
        relationship_name : str
            Name of the relationship to remove.

        Returns
        -------
        Result
            Result with success status.
        """
        return self._relationships.remove_relationship(model_name, relationship_name)

    # -------------------------------------------------------------------------
    # Index Management
    # -------------------------------------------------------------------------

    def add_index(
        self,
        model_name: str,
        columns: list[str],
        unique: bool = False,
        index_name: str | None = None,
    ) -> Result:
        """
        Add an index to a SQLAlchemy model.

        Parameters
        ----------
        model_name : str
            Name of the model class.
        columns : list[str]
            List of column names to include in the index.
        unique : bool
            Whether the index enforces uniqueness.
        index_name : str | None
            Custom name for the index. Auto-generated if not provided.

        Returns
        -------
        Result
            Result with success status.
        """
        model_file = self.find_model(model_name)
        if not model_file:
            return Result(
                success=False,
                message=f"Model '{model_name}' not found",
            )

        content = model_file.read_text()

        # Generate index name if not provided
        if not index_name:
            index_name = f"ix_{model_name.lower()}_{'_'.join(columns)}"

        # Check if index already exists
        if index_name in content:
            return Result(
                success=False,
                message=f"Index '{index_name}' already exists",
            )

        # Build index definition
        cols_str = ", ".join(f'"{c}"' for c in columns)
        index_class = "Index" if not unique else "Index"
        unique_arg = ", unique=True" if unique else ""
        index_def = f'    __table_args__ = (Index("{index_name}", {cols_str}{unique_arg}),)'

        # Find the class and add __table_args__
        class_pattern = re.compile(
            rf"(class\s+{model_name}\s*\([^)]*\):\s*\n)",
            re.MULTILINE,
        )
        match = class_pattern.search(content)

        if not match:
            return Result(
                success=False,
                message=f"Model class '{model_name}' not found in {model_file}",
            )

        # Check if __table_args__ already exists
        if "__table_args__" in content:
            # Append to existing __table_args__
            table_args_pattern = re.compile(
                r"(__table_args__\s*=\s*\()([^)]*)\)",
            )
            ta_match = table_args_pattern.search(content)
            if ta_match:
                existing = ta_match.group(2).rstrip().rstrip(",")
                new_index = f'Index("{index_name}", {cols_str}{unique_arg})'
                new_content = table_args_pattern.sub(
                    rf"\g<1>{existing}, {new_index},)",
                    content,
                )
            else:
                return Result(
                    success=False,
                    message="Could not parse existing __table_args__",
                )
        else:
            # Add new __table_args__ after class definition
            insert_pos = match.end()
            # Find first attribute or method
            new_content = content[:insert_pos] + index_def + "\n\n" + content[insert_pos:]

        # Ensure Index is imported
        if "from sqlalchemy import" in new_content:
            if "Index" not in new_content:
                new_content = re.sub(
                    r"(from sqlalchemy import)([^\n]+)",
                    r"\1 Index,\2",
                    new_content,
                    count=1,
                )
        elif "from sqlalchemy.schema import" not in new_content:
            new_content = "from sqlalchemy import Index\n" + new_content

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add index '{index_name}' to '{model_name}'",
                files_changed=[model_file],
            )

        model_file.write_text(new_content)

        return Result(
            success=True,
            message=f"Added index '{index_name}' to '{model_name}'",
            files_changed=[model_file],
        )

    # -------------------------------------------------------------------------
    # Model Generation
    # -------------------------------------------------------------------------

    def generate_model(
        self,
        model_name: str,
        tablename: str,
        columns: dict[str, str],
        file_path: Path | None = None,
    ) -> Result:
        """
        Generate a new SQLAlchemy model.

        Parameters
        ----------
        model_name : str
            Name of the model class.
        tablename : str
            Database table name.
        columns : dict[str, str]
            Dict mapping column name to SQLAlchemy type string.
        file_path : Path | None
            File to write model to.

        Returns
        -------
        Result
            Result with success status.
        """
        return self._models.generate_model(model_name, tablename, columns, file_path)

    def generate_model_from_table(
        self,
        tablename: str,
        model_name: str | None = None,
        connection_string: str | None = None,
    ) -> Result:
        """
        Generate a SQLAlchemy model by introspecting a database table.

        Parameters
        ----------
        tablename : str
            Database table name.
        model_name : str | None
            Model class name. Defaults to CamelCase of tablename.
        connection_string : str | None
            Database connection string. Uses project config if not provided.

        Returns
        -------
        Result
            Result with success status.
        """
        return self._models.generate_model_from_table(tablename, model_name, connection_string)
