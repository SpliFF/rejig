"""Dunder method generation for Python classes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import libcst as cst


@dataclass
class ClassAttribute:
    """Represents a class attribute."""

    name: str
    type_hint: str | None = None
    default: str | None = None
    has_default: bool = False


class ClassAttributeExtractor(cst.CSTVisitor):
    """Extract class-level attributes from a class body."""

    def __init__(self) -> None:
        self.attributes: list[ClassAttribute] = []
        self._in_init = False
        self._init_assignments: list[ClassAttribute] = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        if node.name.value == "__init__":
            self._in_init = True
        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:
        if node.name.value == "__init__":
            self._in_init = False

    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool:
        """Handle annotated assignments like `name: str = "default"`."""
        if self._in_init:
            # Skip self.x = y assignments inside __init__
            return False

        if not isinstance(node.target, cst.Name):
            return False

        attr_name = node.target.value
        type_hint = None
        default = None
        has_default = False

        # Extract type hint
        if node.annotation:
            type_hint = cst.parse_module("").code_for_node(node.annotation.annotation)

        # Extract default value
        if node.value is not None:
            default = cst.parse_module("").code_for_node(node.value)
            has_default = True

        self.attributes.append(
            ClassAttribute(
                name=attr_name,
                type_hint=type_hint,
                default=default,
                has_default=has_default,
            )
        )
        return False

    def visit_Assign(self, node: cst.Assign) -> bool:
        """Handle simple assignments like `name = "default"`."""
        if self._in_init:
            # Track self.x = y assignments
            for target in node.targets:
                if isinstance(target.target, cst.Attribute):
                    if (
                        isinstance(target.target.value, cst.Name)
                        and target.target.value.value == "self"
                    ):
                        attr_name = target.target.attr.value
                        default = cst.parse_module("").code_for_node(node.value)
                        self._init_assignments.append(
                            ClassAttribute(
                                name=attr_name,
                                type_hint=None,
                                default=default,
                                has_default=True,
                            )
                        )
            return False

        # Class-level assignment
        for target in node.targets:
            if isinstance(target.target, cst.Name):
                attr_name = target.target.value
                default = cst.parse_module("").code_for_node(node.value)
                self.attributes.append(
                    ClassAttribute(
                        name=attr_name,
                        type_hint=None,
                        default=default,
                        has_default=True,
                    )
                )
        return False


def extract_class_attributes(class_node: cst.ClassDef) -> list[ClassAttribute]:
    """Extract all attributes from a class definition.

    Parameters
    ----------
    class_node : cst.ClassDef
        The class definition node.

    Returns
    -------
    list[ClassAttribute]
        List of class attributes with their types and defaults.
    """
    extractor = ClassAttributeExtractor()

    # Walk through class body statements
    for stmt in class_node.body.body:
        if isinstance(stmt, cst.SimpleStatementLine):
            for s in stmt.body:
                if isinstance(s, cst.AnnAssign):
                    extractor.visit_AnnAssign(s)
                elif isinstance(s, cst.Assign):
                    extractor.visit_Assign(s)
        elif isinstance(stmt, cst.FunctionDef):
            # Process __init__ for self.x assignments
            if stmt.name.value == "__init__":
                extractor._in_init = True
                _extract_init_assignments(stmt, extractor)
                extractor._in_init = False

    # Combine class-level attributes with __init__ assignments
    # (class-level takes precedence)
    existing_names = {attr.name for attr in extractor.attributes}
    for init_attr in extractor._init_assignments:
        if init_attr.name not in existing_names:
            extractor.attributes.append(init_attr)

    return extractor.attributes


def _extract_init_assignments(func_node: cst.FunctionDef, extractor: ClassAttributeExtractor) -> None:
    """Extract self.x = y assignments from __init__."""
    for stmt in func_node.body.body:
        if isinstance(stmt, cst.SimpleStatementLine):
            for s in stmt.body:
                if isinstance(s, cst.Assign):
                    for target in s.targets:
                        if isinstance(target.target, cst.Attribute):
                            if (
                                isinstance(target.target.value, cst.Name)
                                and target.target.value.value == "self"
                            ):
                                attr_name = target.target.attr.value
                                default = cst.parse_module("").code_for_node(s.value)
                                extractor._init_assignments.append(
                                    ClassAttribute(
                                        name=attr_name,
                                        type_hint=None,
                                        default=default,
                                        has_default=True,
                                    )
                                )


class DunderGenerator:
    """Generate dunder methods for a class.

    Parameters
    ----------
    attributes : Sequence[ClassAttribute]
        Class attributes to use for generation.

    Examples
    --------
    >>> attrs = [ClassAttribute("name", "str"), ClassAttribute("age", "int", "0")]
    >>> gen = DunderGenerator(attrs)
    >>> init_code = gen.generate_init()
    """

    def __init__(self, attributes: Sequence[ClassAttribute]) -> None:
        self.attributes = list(attributes)

    def generate_init(self) -> str:
        """Generate __init__ method from attributes.

        Returns
        -------
        str
            Source code for __init__ method.
        """
        if not self.attributes:
            return "def __init__(self) -> None:\n    pass"

        # Build parameters
        params = ["self"]
        for attr in self.attributes:
            if attr.type_hint:
                if attr.has_default and attr.default:
                    params.append(f"{attr.name}: {attr.type_hint} = {attr.default}")
                else:
                    params.append(f"{attr.name}: {attr.type_hint}")
            else:
                if attr.has_default and attr.default:
                    params.append(f"{attr.name}={attr.default}")
                else:
                    params.append(attr.name)

        # Build body
        body_lines = []
        for attr in self.attributes:
            body_lines.append(f"self.{attr.name} = {attr.name}")

        if not body_lines:
            body_lines = ["pass"]

        param_str = ", ".join(params)
        body_str = "\n    ".join(body_lines)
        return f"def __init__({param_str}) -> None:\n    {body_str}"

    def generate_repr(self) -> str:
        """Generate __repr__ method from attributes.

        Returns
        -------
        str
            Source code for __repr__ method.
        """
        if not self.attributes:
            return 'def __repr__(self) -> str:\n    return f"{self.__class__.__name__}()"'

        # Build repr string parts
        parts = []
        for attr in self.attributes:
            parts.append(f"{attr.name}={{self.{attr.name}!r}}")

        repr_parts = ", ".join(parts)
        return f'def __repr__(self) -> str:\n    return f"{{self.__class__.__name__}}({repr_parts})"'

    def generate_eq(self) -> str:
        """Generate __eq__ method from attributes.

        Returns
        -------
        str
            Source code for __eq__ method.
        """
        if not self.attributes:
            return "def __eq__(self, other: object) -> bool:\n    return isinstance(other, self.__class__)"

        # Build comparison
        comparisons = []
        for attr in self.attributes:
            comparisons.append(f"self.{attr.name} == other.{attr.name}")

        comparison_str = " and ".join(comparisons)
        return f"def __eq__(self, other: object) -> bool:\n    if not isinstance(other, self.__class__):\n        return NotImplemented\n    return {comparison_str}"

    def generate_hash(self) -> str:
        """Generate __hash__ method from attributes.

        Returns
        -------
        str
            Source code for __hash__ method.
        """
        if not self.attributes:
            return "def __hash__(self) -> int:\n    return hash(())"

        # Build hash tuple
        hash_parts = ", ".join(f"self.{attr.name}" for attr in self.attributes)
        return f"def __hash__(self) -> int:\n    return hash(({hash_parts},))"


class GenerateInitTransformer(cst.CSTTransformer):
    """Transformer to add or replace __init__ method.

    Parameters
    ----------
    class_name : str
        Name of the class to modify.
    overwrite : bool
        If True, replace existing __init__. Default False.
    """

    def __init__(self, class_name: str, overwrite: bool = False):
        super().__init__()
        self.class_name = class_name
        self.overwrite = overwrite
        self.added = False

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value != self.class_name:
            return updated_node

        # Extract attributes
        attributes = extract_class_attributes(updated_node)

        # Check if __init__ already exists
        has_init = False
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                has_init = True
                break

        if has_init and not self.overwrite:
            return updated_node

        # Generate new __init__
        generator = DunderGenerator(attributes)
        init_code = generator.generate_init()
        init_node = cst.parse_statement(init_code)

        if has_init and self.overwrite:
            # Replace existing __init__
            new_body = []
            for stmt in updated_node.body.body:
                if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                    new_body.append(init_node)
                else:
                    new_body.append(stmt)
            self.added = True
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=new_body)
            )
        else:
            # Insert __init__ after docstring and class attributes
            new_body = list(updated_node.body.body)
            insert_idx = 0

            # Skip past docstring if present
            if new_body and isinstance(new_body[0], cst.SimpleStatementLine):
                if len(new_body[0].body) == 1 and isinstance(new_body[0].body[0], cst.Expr):
                    expr = new_body[0].body[0].value
                    if isinstance(expr, (cst.SimpleString, cst.ConcatenatedString, cst.FormattedString)):
                        insert_idx = 1

            # Skip past class-level attributes
            while insert_idx < len(new_body):
                stmt = new_body[insert_idx]
                if isinstance(stmt, cst.SimpleStatementLine):
                    # Could be an attribute
                    if any(
                        isinstance(s, (cst.AnnAssign, cst.Assign))
                        for s in stmt.body
                    ):
                        insert_idx += 1
                        continue
                break

            new_body.insert(insert_idx, init_node)
            self.added = True
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=new_body)
            )


class GenerateReprTransformer(cst.CSTTransformer):
    """Transformer to add or replace __repr__ method.

    Parameters
    ----------
    class_name : str
        Name of the class to modify.
    overwrite : bool
        If True, replace existing __repr__. Default False.
    """

    def __init__(self, class_name: str, overwrite: bool = False):
        super().__init__()
        self.class_name = class_name
        self.overwrite = overwrite
        self.added = False

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value != self.class_name:
            return updated_node

        attributes = extract_class_attributes(updated_node)

        has_repr = False
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__repr__":
                has_repr = True
                break

        if has_repr and not self.overwrite:
            return updated_node

        generator = DunderGenerator(attributes)
        repr_code = generator.generate_repr()
        repr_node = cst.parse_statement(repr_code)

        if has_repr and self.overwrite:
            new_body = []
            for stmt in updated_node.body.body:
                if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__repr__":
                    new_body.append(repr_node)
                else:
                    new_body.append(stmt)
            self.added = True
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=new_body)
            )
        else:
            # Insert at end of class
            new_body = list(updated_node.body.body) + [repr_node]
            self.added = True
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=new_body)
            )


class GenerateEqTransformer(cst.CSTTransformer):
    """Transformer to add or replace __eq__ method.

    Parameters
    ----------
    class_name : str
        Name of the class to modify.
    overwrite : bool
        If True, replace existing __eq__. Default False.
    """

    def __init__(self, class_name: str, overwrite: bool = False):
        super().__init__()
        self.class_name = class_name
        self.overwrite = overwrite
        self.added = False

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value != self.class_name:
            return updated_node

        attributes = extract_class_attributes(updated_node)

        has_eq = False
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__eq__":
                has_eq = True
                break

        if has_eq and not self.overwrite:
            return updated_node

        generator = DunderGenerator(attributes)
        eq_code = generator.generate_eq()
        eq_node = cst.parse_statement(eq_code)

        if has_eq and self.overwrite:
            new_body = []
            for stmt in updated_node.body.body:
                if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__eq__":
                    new_body.append(eq_node)
                else:
                    new_body.append(stmt)
            self.added = True
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=new_body)
            )
        else:
            new_body = list(updated_node.body.body) + [eq_node]
            self.added = True
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=new_body)
            )


class GenerateHashTransformer(cst.CSTTransformer):
    """Transformer to add or replace __hash__ method.

    Parameters
    ----------
    class_name : str
        Name of the class to modify.
    overwrite : bool
        If True, replace existing __hash__. Default False.
    """

    def __init__(self, class_name: str, overwrite: bool = False):
        super().__init__()
        self.class_name = class_name
        self.overwrite = overwrite
        self.added = False

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value != self.class_name:
            return updated_node

        attributes = extract_class_attributes(updated_node)

        has_hash = False
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__hash__":
                has_hash = True
                break

        if has_hash and not self.overwrite:
            return updated_node

        generator = DunderGenerator(attributes)
        hash_code = generator.generate_hash()
        hash_node = cst.parse_statement(hash_code)

        if has_hash and self.overwrite:
            new_body = []
            for stmt in updated_node.body.body:
                if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__hash__":
                    new_body.append(hash_node)
                else:
                    new_body.append(stmt)
            self.added = True
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=new_body)
            )
        else:
            new_body = list(updated_node.body.body) + [hash_node]
            self.added = True
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=new_body)
            )
