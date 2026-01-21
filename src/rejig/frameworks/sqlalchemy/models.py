"""Model management for SQLAlchemy applications.

This module provides the ModelManager class for managing SQLAlchemy
model definitions, columns, and related operations.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result

if TYPE_CHECKING:
    from .project import SQLAlchemyProject


class ModelManager:
    """Manages SQLAlchemy models and columns."""

    def __init__(self, project: SQLAlchemyProject):
        self.project = project

    @property
    def dry_run(self) -> bool:
        return self.project.dry_run

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
            Path to file, or None if not found.
        """
        models_path = self.project.models_path

        # If it's a file, check directly
        if models_path.is_file():
            content = models_path.read_text()
            if re.search(rf"\bclass\s+{model_name}\s*\(", content):
                return models_path
            return None

        # Search directory
        if models_path.is_dir():
            for py_file in models_path.rglob("*.py"):
                if "__pycache__" in str(py_file):
                    continue
                try:
                    content = py_file.read_text()
                    if re.search(rf"\bclass\s+{model_name}\s*\(", content):
                        return py_file
                except (OSError, UnicodeDecodeError):
                    continue

        # Search entire project as fallback
        for py_file in self.project.project_root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                content = py_file.read_text()
                if re.search(rf"\bclass\s+{model_name}\s*\(", content):
                    return py_file
            except (OSError, UnicodeDecodeError):
                continue

        return None

    def list_models(self) -> list[dict[str, str]]:
        """
        List all SQLAlchemy models in the project.

        Returns
        -------
        list[dict[str, str]]
            List of dicts with model information.
        """
        models: list[dict[str, str]] = []

        # Find all files to search
        search_paths: list[Path] = []
        if self.project.models_path.is_file():
            search_paths = [self.project.models_path]
        elif self.project.models_path.is_dir():
            search_paths = list(self.project.models_path.rglob("*.py"))
        else:
            search_paths = list(self.project.project_root.rglob("*.py"))

        for py_file in search_paths:
            if "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text()
            except (OSError, UnicodeDecodeError):
                continue

            # Find SQLAlchemy model classes
            # Look for classes inheriting from Base, db.Model, DeclarativeBase, etc.
            model_pattern = re.compile(
                r"class\s+(\w+)\s*\(\s*(?:Base|db\.Model|DeclarativeBase|SQLModel)[^)]*\):",
                re.MULTILINE,
            )

            for match in model_pattern.finditer(content):
                model_name = match.group(1)

                # Try to find __tablename__
                tablename_pattern = re.compile(
                    rf"class\s+{model_name}[^:]+:.*?__tablename__\s*=\s*['\"](\w+)['\"]",
                    re.DOTALL,
                )
                tn_match = tablename_pattern.search(content)
                tablename = tn_match.group(1) if tn_match else model_name.lower()

                models.append({
                    "name": model_name,
                    "tablename": tablename,
                    "file": str(py_file),
                })

        return models

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
            List of dicts with column information.
        """
        model_file = self.find_model(model_name)
        if not model_file:
            return []

        content = model_file.read_text()
        columns: list[dict[str, str]] = []

        # Find the class definition
        class_pattern = re.compile(
            rf"class\s+{model_name}\s*\([^)]*\):\s*\n(.*?)(?=\nclass\s|\Z)",
            re.DOTALL,
        )
        class_match = class_pattern.search(content)
        if not class_match:
            return []

        class_body = class_match.group(1)

        # Match Column definitions
        # Handles: name = Column(Type, ...) and name: Mapped[type] = mapped_column(...)
        column_pattern = re.compile(
            r"(\w+)\s*(?::\s*\w+\[[^\]]+\])?\s*=\s*(?:Column|mapped_column)\s*\(([^)]+)\)",
        )

        for match in column_pattern.finditer(class_body):
            col_name = match.group(1)
            col_args = match.group(2)

            # Parse column type (first arg or type= keyword)
            type_match = re.match(r"(\w+(?:\([^)]*\))?)", col_args)
            col_type = type_match.group(1) if type_match else "Unknown"

            # Check for nullable
            nullable = "nullable=False" not in col_args

            # Check for primary_key
            primary_key = "primary_key=True" in col_args

            columns.append({
                "name": col_name,
                "type": col_type,
                "nullable": str(nullable),
                "primary_key": str(primary_key),
            })

        return columns

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
            SQLAlchemy type.
        nullable : bool
            Whether the column allows NULL.
        default : str | None
            Default value expression.
        primary_key : bool
            Whether this is a primary key.
        unique : bool
            Whether values must be unique.
        index : bool
            Whether to create an index.
        foreign_key : str | None
            Foreign key reference.

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

        # Check if column already exists
        if re.search(rf"\b{column_name}\s*=\s*(?:Column|mapped_column)", content):
            return Result(
                success=False,
                message=f"Column '{column_name}' already exists in '{model_name}'",
            )

        # Build column definition
        col_args = [column_type]

        if foreign_key:
            col_args.append(f'ForeignKey("{foreign_key}")')
        if primary_key:
            col_args.append("primary_key=True")
        if not nullable:
            col_args.append("nullable=False")
        if unique:
            col_args.append("unique=True")
        if index:
            col_args.append("index=True")
        if default:
            col_args.append(f"default={default}")

        column_def = f"    {column_name} = Column({', '.join(col_args)})"

        # Find insertion point - after __tablename__ or other columns
        class_pattern = re.compile(
            rf"(class\s+{model_name}\s*\([^)]*\):\s*\n"
            r"(?:[ \t]+[^\n]*\n)*)"  # Capture class body
            r"([ \t]*\n)",  # Blank line before next element
            re.MULTILINE,
        )

        match = class_pattern.search(content)
        if not match:
            # Simple pattern - just find the class
            simple_pattern = re.compile(
                rf"(class\s+{model_name}\s*\([^)]*\):\s*\n)",
                re.MULTILINE,
            )
            match = simple_pattern.search(content)
            if not match:
                return Result(
                    success=False,
                    message=f"Could not find class '{model_name}' in {model_file}",
                )
            # Insert after class definition
            insert_pos = match.end()
            new_content = content[:insert_pos] + column_def + "\n" + content[insert_pos:]
        else:
            # Insert before the blank line
            insert_pos = match.end(1)
            new_content = content[:insert_pos] + column_def + "\n" + content[insert_pos:]

        # Ensure Column is imported
        if "from sqlalchemy import" in new_content:
            if "Column" not in new_content:
                new_content = re.sub(
                    r"(from sqlalchemy import)([^\n]+)",
                    r"\1 Column,\2",
                    new_content,
                    count=1,
                )
            # Also ensure the type is imported
            base_type = column_type.split("(")[0]
            if base_type not in new_content and base_type not in ("Column", "ForeignKey"):
                new_content = re.sub(
                    r"(from sqlalchemy import)([^\n]+)",
                    rf"\1 {base_type},\2",
                    new_content,
                    count=1,
                )

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add column '{column_name}' to '{model_name}'",
                files_changed=[model_file],
            )

        model_file.write_text(new_content)

        return Result(
            success=True,
            message=f"Added column '{column_name}' to '{model_name}'",
            files_changed=[model_file],
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
        model_file = self.find_model(model_name)
        if not model_file:
            return Result(
                success=False,
                message=f"Model '{model_name}' not found",
            )

        content = model_file.read_text()

        # Remove the column definition
        pattern = re.compile(
            rf"^\s*{column_name}\s*(?::\s*\w+\[[^\]]+\])?\s*=\s*(?:Column|mapped_column)\s*\([^)]+\)\s*\n",
            re.MULTILINE,
        )

        if not pattern.search(content):
            return Result(
                success=False,
                message=f"Column '{column_name}' not found in '{model_name}'",
            )

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would remove column '{column_name}' from '{model_name}'",
                files_changed=[model_file],
            )

        new_content = pattern.sub("", content)
        model_file.write_text(new_content)

        return Result(
            success=True,
            message=f"Removed column '{column_name}' from '{model_name}'",
            files_changed=[model_file],
        )

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
        model_file = self.find_model(model_name)
        if not model_file:
            return Result(
                success=False,
                message=f"Model '{model_name}' not found",
            )

        content = model_file.read_text()

        # Find and rename the column
        pattern = re.compile(
            rf"^(\s*){old_name}(\s*(?::\s*\w+\[[^\]]+\])?\s*=\s*(?:Column|mapped_column)\s*\([^)]+\))",
            re.MULTILINE,
        )

        if not pattern.search(content):
            return Result(
                success=False,
                message=f"Column '{old_name}' not found in '{model_name}'",
            )

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would rename column '{old_name}' to '{new_name}' in '{model_name}'",
                files_changed=[model_file],
            )

        new_content = pattern.sub(rf"\g<1>{new_name}\g<2>", content)
        model_file.write_text(new_content)

        return Result(
            success=True,
            message=f"Renamed column '{old_name}' to '{new_name}' in '{model_name}'",
            files_changed=[model_file],
        )

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
            Dict mapping column name to type string.
        file_path : Path | None
            File to write model to.

        Returns
        -------
        Result
            Result with success status.
        """
        # Determine target file
        if file_path:
            target_file = Path(file_path)
        elif self.project.models_path.is_file():
            target_file = self.project.models_path
        else:
            self.project.models_path.mkdir(exist_ok=True)
            target_file = self.project.models_path / f"{tablename}.py"

        # Build column definitions
        column_lines: list[str] = []
        imports: set[str] = {"Column"}

        for col_name, col_type in columns.items():
            base_type = col_type.split("(")[0]
            imports.add(base_type)
            column_lines.append(f"    {col_name} = Column({col_type})")

        columns_code = "\n".join(column_lines) if column_lines else "    pass"
        imports_str = ", ".join(sorted(imports))

        model_code = f'''"""SQLAlchemy model for {tablename} table."""
from sqlalchemy import {imports_str}
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class {model_name}(Base):
    """Model for {tablename} table."""

    __tablename__ = "{tablename}"

{columns_code}
'''

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would generate model '{model_name}'",
                files_changed=[target_file],
            )

        # If file exists and model doesn't, append
        if target_file.exists():
            content = target_file.read_text()
            if re.search(rf"\bclass\s+{model_name}\s*\(", content):
                return Result(
                    success=False,
                    message=f"Model '{model_name}' already exists in {target_file}",
                )
            # Append model class only
            class_code = f'''

class {model_name}(Base):
    """Model for {tablename} table."""

    __tablename__ = "{tablename}"

{columns_code}
'''
            target_file.write_text(content.rstrip() + class_code)
        else:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(model_code)

        return Result(
            success=True,
            message=f"Generated model '{model_name}'",
            files_changed=[target_file],
        )

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
            Model class name.
        connection_string : str | None
            Database connection string.

        Returns
        -------
        Result
            Result with success status.
        """
        if not connection_string:
            return Result(
                success=False,
                message="Connection string required for table introspection",
            )

        try:
            from sqlalchemy import create_engine, inspect
        except ImportError:
            return Result(
                success=False,
                message="SQLAlchemy must be installed for table introspection",
            )

        # Generate model name from table name if not provided
        if not model_name:
            # Convert snake_case to CamelCase
            parts = tablename.split("_")
            model_name = "".join(p.capitalize() for p in parts)

        try:
            engine = create_engine(connection_string)
            inspector = inspect(engine)

            if tablename not in inspector.get_table_names():
                return Result(
                    success=False,
                    message=f"Table '{tablename}' not found in database",
                )

            columns = inspector.get_columns(tablename)
            pk_cols = {c["name"] for c in inspector.get_pk_constraint(tablename).get("constrained_columns", [])}

            # Map SQL types to SQLAlchemy types
            type_map = {
                "INTEGER": "Integer",
                "BIGINT": "BigInteger",
                "SMALLINT": "SmallInteger",
                "VARCHAR": "String",
                "TEXT": "Text",
                "BOOLEAN": "Boolean",
                "DATE": "Date",
                "DATETIME": "DateTime",
                "TIMESTAMP": "DateTime",
                "FLOAT": "Float",
                "NUMERIC": "Numeric",
                "DECIMAL": "Numeric",
            }

            column_defs: dict[str, str] = {}
            for col in columns:
                col_name = col["name"]
                sql_type = str(col["type"]).upper().split("(")[0]
                sqla_type = type_map.get(sql_type, "String")

                # Handle varchar length
                if "VARCHAR" in str(col["type"]).upper():
                    length_match = re.search(r"\((\d+)\)", str(col["type"]))
                    if length_match:
                        sqla_type = f"String({length_match.group(1)})"

                # Build column args
                args = [sqla_type]
                if col_name in pk_cols:
                    args.append("primary_key=True")
                if not col.get("nullable", True):
                    args.append("nullable=False")

                column_defs[col_name] = ", ".join(args)

        except Exception as e:
            return Result(
                success=False,
                message=f"Error introspecting table: {e}",
            )

        return self.generate_model(model_name, tablename, column_defs)
