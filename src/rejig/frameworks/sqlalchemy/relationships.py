"""Relationship management for SQLAlchemy applications.

This module provides the RelationshipManager class for managing SQLAlchemy
model relationships.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result

if TYPE_CHECKING:
    from .project import SQLAlchemyProject


class RelationshipManager:
    """Manages relationships in SQLAlchemy models."""

    def __init__(self, project: SQLAlchemyProject):
        self.project = project

    @property
    def dry_run(self) -> bool:
        return self.project.dry_run

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
            List of dicts with relationship information.
        """
        model_file = self.project._models.find_model(model_name)
        if not model_file:
            return []

        content = model_file.read_text()
        relationships: list[dict[str, str]] = []

        # Find relationships in the class
        # Handles: rel = relationship("Target", ...) and rel: Mapped["Target"] = relationship(...)
        rel_pattern = re.compile(
            r"(\w+)\s*(?::\s*\w+\[[^\]]+\])?\s*=\s*relationship\s*\(\s*['\"](\w+)['\"]"
            r"(?:[^)]*back_populates\s*=\s*['\"](\w+)['\"])?"
            r"(?:[^)]*backref\s*=\s*['\"](\w+)['\"])?"
            r"[^)]*\)",
        )

        for match in rel_pattern.finditer(content):
            rel_name = match.group(1)
            target = match.group(2)
            back_populates = match.group(3) or ""
            backref = match.group(4) or ""

            relationships.append({
                "name": rel_name,
                "target": target,
                "back_populates": back_populates,
                "backref": backref,
            })

        return relationships

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
            Alternative to back_populates.
        lazy : str
            Loading strategy.
        uselist : bool | None
            If False, relationship is scalar.
        foreign_keys : str | None
            Explicit foreign key column(s).

        Returns
        -------
        Result
            Result with success status.
        """
        model_file = self.project._models.find_model(model_name)
        if not model_file:
            return Result(
                success=False,
                message=f"Model '{model_name}' not found",
            )

        content = model_file.read_text()

        # Check if relationship already exists
        if re.search(rf"\b{relationship_name}\s*=\s*relationship", content):
            return Result(
                success=False,
                message=f"Relationship '{relationship_name}' already exists in '{model_name}'",
            )

        # Build relationship definition
        rel_args = [f'"{target_model}"']

        if back_populates:
            rel_args.append(f'back_populates="{back_populates}"')
        elif backref:
            rel_args.append(f'backref="{backref}"')

        if lazy != "select":
            rel_args.append(f'lazy="{lazy}"')

        if uselist is not None:
            rel_args.append(f"uselist={uselist}")

        if foreign_keys:
            rel_args.append(f"foreign_keys=[{foreign_keys}]")

        rel_def = f"    {relationship_name} = relationship({', '.join(rel_args)})"

        # Find insertion point - at end of class columns/relationships
        class_pattern = re.compile(
            rf"(class\s+{model_name}\s*\([^)]*\):\s*\n"
            r"(?:[ \t]+[^\n]*\n)*)",  # Capture class body
            re.MULTILINE,
        )

        match = class_pattern.search(content)
        if not match:
            return Result(
                success=False,
                message=f"Could not find class '{model_name}' in {model_file}",
            )

        # Insert at the end of the class body
        insert_pos = match.end()
        # Walk back to find the actual last line of the class
        lines = content[:insert_pos].splitlines()
        while lines and not lines[-1].strip():
            lines.pop()
            insert_pos -= 1

        new_content = content[:insert_pos] + "\n" + rel_def + "\n" + content[insert_pos:]

        # Ensure relationship is imported
        if "from sqlalchemy.orm import" in new_content:
            if "relationship" not in new_content:
                new_content = re.sub(
                    r"(from sqlalchemy\.orm import)([^\n]+)",
                    r"\1 relationship,\2",
                    new_content,
                    count=1,
                )
        elif "from sqlalchemy import" in new_content:
            # Add orm import
            new_content = re.sub(
                r"(from sqlalchemy import[^\n]+\n)",
                r"\1from sqlalchemy.orm import relationship\n",
                new_content,
                count=1,
            )
        else:
            new_content = "from sqlalchemy.orm import relationship\n" + new_content

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add relationship '{relationship_name}' to '{model_name}'",
                files_changed=[model_file],
            )

        model_file.write_text(new_content)

        return Result(
            success=True,
            message=f"Added relationship '{relationship_name}' to '{model_name}'",
            files_changed=[model_file],
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
        model_file = self.project._models.find_model(model_name)
        if not model_file:
            return Result(
                success=False,
                message=f"Model '{model_name}' not found",
            )

        content = model_file.read_text()

        # Remove the relationship definition
        pattern = re.compile(
            rf"^\s*{relationship_name}\s*(?::\s*\w+\[[^\]]+\])?\s*=\s*relationship\s*\([^)]+\)\s*\n",
            re.MULTILINE,
        )

        if not pattern.search(content):
            return Result(
                success=False,
                message=f"Relationship '{relationship_name}' not found in '{model_name}'",
            )

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would remove relationship '{relationship_name}' from '{model_name}'",
                files_changed=[model_file],
            )

        new_content = pattern.sub("", content)
        model_file.write_text(new_content)

        return Result(
            success=True,
            message=f"Removed relationship '{relationship_name}' from '{model_name}'",
            files_changed=[model_file],
        )

    def add_bidirectional_relationship(
        self,
        model1_name: str,
        rel1_name: str,
        model2_name: str,
        rel2_name: str,
        lazy: str = "select",
    ) -> Result:
        """
        Add a bidirectional relationship between two models.

        Parameters
        ----------
        model1_name : str
            Name of the first model.
        rel1_name : str
            Relationship name on first model.
        model2_name : str
            Name of the second model.
        rel2_name : str
            Relationship name on second model.
        lazy : str
            Loading strategy for both relationships.

        Returns
        -------
        Result
            Result with success status.
        """
        # Add relationship on first model
        result1 = self.add_relationship(
            model1_name,
            rel1_name,
            model2_name,
            back_populates=rel2_name,
            lazy=lazy,
        )

        if not result1.success:
            return result1

        # Add relationship on second model
        result2 = self.add_relationship(
            model2_name,
            rel2_name,
            model1_name,
            back_populates=rel1_name,
            lazy=lazy,
        )

        if not result2.success:
            return Result(
                success=False,
                message=f"Added {rel1_name} to {model1_name} but failed to add {rel2_name} to {model2_name}: {result2.message}",
                files_changed=result1.files_changed,
            )

        return Result(
            success=True,
            message=f"Added bidirectional relationship between '{model1_name}' and '{model2_name}'",
            files_changed=list(set(result1.files_changed + result2.files_changed)),
        )
