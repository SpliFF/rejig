"""Class conversion transformers for dataclass, TypedDict, NamedTuple, etc."""
from __future__ import annotations

import libcst as cst
from libcst import matchers as m

from .dunder import ClassAttribute, extract_class_attributes


class ConvertToDataclassTransformer(cst.CSTTransformer):
    """Convert a regular class to a dataclass.

    This transformer:
    1. Adds the @dataclass decorator
    2. Converts instance attributes to class-level annotated attributes
    3. Removes manual __init__ if it only does attribute assignment

    Parameters
    ----------
    class_name : str
        Name of the class to convert.
    frozen : bool
        If True, add frozen=True to the decorator. Default False.
    slots : bool
        If True, add slots=True to the decorator (Python 3.10+). Default False.
    """

    def __init__(
        self,
        class_name: str,
        frozen: bool = False,
        slots: bool = False,
    ):
        super().__init__()
        self.class_name = class_name
        self.frozen = frozen
        self.slots = slots
        self.converted = False
        self._attributes: list[ClassAttribute] = []

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value != self.class_name:
            return updated_node

        # Check if already a dataclass
        for dec in updated_node.decorators:
            if isinstance(dec.decorator, cst.Name) and dec.decorator.value == "dataclass":
                return updated_node
            if isinstance(dec.decorator, cst.Call):
                if isinstance(dec.decorator.func, cst.Name) and dec.decorator.func.value == "dataclass":
                    return updated_node

        # Extract attributes
        self._attributes = extract_class_attributes(updated_node)

        # Build dataclass decorator
        args = []
        if self.frozen:
            args.append(cst.Arg(keyword=cst.Name("frozen"), value=cst.Name("True")))
        if self.slots:
            args.append(cst.Arg(keyword=cst.Name("slots"), value=cst.Name("True")))

        if args:
            decorator_expr = cst.Call(func=cst.Name("dataclass"), args=args)
        else:
            decorator_expr = cst.Name("dataclass")

        new_decorator = cst.Decorator(decorator=decorator_expr)
        new_decorators = [new_decorator] + list(updated_node.decorators)

        # Build new class body with dataclass-style attributes
        new_body: list[cst.BaseStatement] = []

        # Keep docstring if present
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                if len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Expr):
                    expr = stmt.body[0].value
                    if isinstance(expr, (cst.SimpleString, cst.ConcatenatedString, cst.FormattedString)):
                        new_body.append(stmt)
                        break

        # Add annotated attributes
        for attr in self._attributes:
            if attr.type_hint:
                if attr.has_default and attr.default:
                    ann_assign = cst.AnnAssign(
                        target=cst.Name(attr.name),
                        annotation=cst.Annotation(annotation=cst.parse_expression(attr.type_hint)),
                        value=cst.parse_expression(attr.default),
                    )
                else:
                    ann_assign = cst.AnnAssign(
                        target=cst.Name(attr.name),
                        annotation=cst.Annotation(annotation=cst.parse_expression(attr.type_hint)),
                        value=None,
                    )
            else:
                # No type hint - use Any
                if attr.has_default and attr.default:
                    ann_assign = cst.AnnAssign(
                        target=cst.Name(attr.name),
                        annotation=cst.Annotation(annotation=cst.Name("Any")),
                        value=cst.parse_expression(attr.default),
                    )
                else:
                    ann_assign = cst.AnnAssign(
                        target=cst.Name(attr.name),
                        annotation=cst.Annotation(annotation=cst.Name("Any")),
                        value=None,
                    )
            new_body.append(cst.SimpleStatementLine(body=[ann_assign]))

        # Keep non-__init__ methods
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value != "__init__":
                    new_body.append(stmt)
            elif isinstance(stmt, cst.ClassDef):
                # Keep nested classes
                new_body.append(stmt)

        # If no attributes and no methods, add pass
        if len(new_body) == 0 or (
            len(new_body) == 1
            and isinstance(new_body[0], cst.SimpleStatementLine)
            and isinstance(new_body[0].body[0], cst.Expr)
        ):
            new_body.append(cst.SimpleStatementLine(body=[cst.Pass()]))

        self.converted = True
        return updated_node.with_changes(
            decorators=new_decorators,
            body=updated_node.body.with_changes(body=new_body),
        )


class ConvertFromDataclassTransformer(cst.CSTTransformer):
    """Convert a dataclass back to a regular class.

    This transformer:
    1. Removes the @dataclass decorator
    2. Generates an __init__ method from the attributes
    3. Optionally generates __repr__, __eq__, __hash__

    Parameters
    ----------
    class_name : str
        Name of the class to convert.
    generate_repr : bool
        If True, generate __repr__ method. Default True.
    generate_eq : bool
        If True, generate __eq__ method. Default True.
    generate_hash : bool
        If True, generate __hash__ method. Default False.
    """

    def __init__(
        self,
        class_name: str,
        generate_repr: bool = True,
        generate_eq: bool = True,
        generate_hash: bool = False,
    ):
        super().__init__()
        self.class_name = class_name
        self.generate_repr = generate_repr
        self.generate_eq = generate_eq
        self.generate_hash = generate_hash
        self.converted = False

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value != self.class_name:
            return updated_node

        # Check if it's actually a dataclass
        is_dataclass = False
        new_decorators = []
        for dec in updated_node.decorators:
            is_dc = False
            if isinstance(dec.decorator, cst.Name) and dec.decorator.value == "dataclass":
                is_dc = True
                is_dataclass = True
            elif isinstance(dec.decorator, cst.Call):
                if isinstance(dec.decorator.func, cst.Name) and dec.decorator.func.value == "dataclass":
                    is_dc = True
                    is_dataclass = True

            if not is_dc:
                new_decorators.append(dec)

        if not is_dataclass:
            return updated_node

        # Extract attributes
        attributes = extract_class_attributes(updated_node)

        # Import the generator
        from .dunder import DunderGenerator

        generator = DunderGenerator(attributes)

        # Build new class body
        new_body: list[cst.BaseStatement] = []

        # Keep docstring if present
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                if len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Expr):
                    expr = stmt.body[0].value
                    if isinstance(expr, (cst.SimpleString, cst.ConcatenatedString, cst.FormattedString)):
                        new_body.append(stmt)
                        break

        # Keep class attributes (but they'll become instance attributes via __init__)
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for s in stmt.body:
                    if isinstance(s, cst.AnnAssign):
                        new_body.append(stmt)
                        break

        # Generate __init__
        init_code = generator.generate_init()
        new_body.append(cst.parse_statement(init_code))

        # Generate __repr__ if requested
        if self.generate_repr:
            repr_code = generator.generate_repr()
            new_body.append(cst.parse_statement(repr_code))

        # Generate __eq__ if requested
        if self.generate_eq:
            eq_code = generator.generate_eq()
            new_body.append(cst.parse_statement(eq_code))

        # Generate __hash__ if requested
        if self.generate_hash:
            hash_code = generator.generate_hash()
            new_body.append(cst.parse_statement(hash_code))

        # Keep other methods (excluding dunder methods if we're generating them)
        excluded_methods = {"__init__"}
        if self.generate_repr:
            excluded_methods.add("__repr__")
        if self.generate_eq:
            excluded_methods.add("__eq__")
        if self.generate_hash:
            excluded_methods.add("__hash__")

        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value not in excluded_methods:
                    new_body.append(stmt)
            elif isinstance(stmt, cst.ClassDef):
                new_body.append(stmt)

        self.converted = True
        return updated_node.with_changes(
            decorators=new_decorators if new_decorators else [],
            body=updated_node.body.with_changes(body=new_body),
        )


class ConvertToTypedDictTransformer(cst.CSTTransformer):
    """Convert a class or dataclass to a TypedDict.

    Parameters
    ----------
    class_name : str
        Name of the class to convert.
    total : bool
        If True, all keys are required. Default True.
    """

    def __init__(self, class_name: str, total: bool = True):
        super().__init__()
        self.class_name = class_name
        self.total = total
        self.converted = False

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value != self.class_name:
            return updated_node

        # Extract attributes
        attributes = extract_class_attributes(updated_node)

        # Build new class body with just type annotations
        new_body: list[cst.BaseStatement] = []

        # Keep docstring if present
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                if len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Expr):
                    expr = stmt.body[0].value
                    if isinstance(expr, (cst.SimpleString, cst.ConcatenatedString, cst.FormattedString)):
                        new_body.append(stmt)
                        break

        # Add type annotations only (no defaults)
        for attr in attributes:
            type_hint = attr.type_hint or "Any"
            ann_assign = cst.AnnAssign(
                target=cst.Name(attr.name),
                annotation=cst.Annotation(annotation=cst.parse_expression(type_hint)),
                value=None,
            )
            new_body.append(cst.SimpleStatementLine(body=[ann_assign]))

        if not new_body or (
            len(new_body) == 1
            and isinstance(new_body[0], cst.SimpleStatementLine)
            and isinstance(new_body[0].body[0], cst.Expr)
        ):
            new_body.append(cst.SimpleStatementLine(body=[cst.Pass()]))

        # Build base class: TypedDict or TypedDict with total
        if self.total:
            base = cst.Arg(value=cst.Name("TypedDict"))
        else:
            # For total=False, we need: class X(TypedDict, total=False)
            # We'll just use TypedDict as base and note that total=False needs import handling
            base = cst.Arg(value=cst.Name("TypedDict"))

        # Remove all decorators
        self.converted = True
        return updated_node.with_changes(
            decorators=[],
            bases=[base],
            body=updated_node.body.with_changes(body=new_body),
        )


class ConvertToNamedTupleTransformer(cst.CSTTransformer):
    """Convert a class or dataclass to a NamedTuple.

    Parameters
    ----------
    class_name : str
        Name of the class to convert.
    """

    def __init__(self, class_name: str):
        super().__init__()
        self.class_name = class_name
        self.converted = False

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value != self.class_name:
            return updated_node

        # Extract attributes
        attributes = extract_class_attributes(updated_node)

        # Build new class body with just type annotations
        new_body: list[cst.BaseStatement] = []

        # Keep docstring if present
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                if len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Expr):
                    expr = stmt.body[0].value
                    if isinstance(expr, (cst.SimpleString, cst.ConcatenatedString, cst.FormattedString)):
                        new_body.append(stmt)
                        break

        # Add type annotations (with defaults if present)
        for attr in attributes:
            type_hint = attr.type_hint or "Any"
            if attr.has_default and attr.default:
                ann_assign = cst.AnnAssign(
                    target=cst.Name(attr.name),
                    annotation=cst.Annotation(annotation=cst.parse_expression(type_hint)),
                    value=cst.parse_expression(attr.default),
                )
            else:
                ann_assign = cst.AnnAssign(
                    target=cst.Name(attr.name),
                    annotation=cst.Annotation(annotation=cst.parse_expression(type_hint)),
                    value=None,
                )
            new_body.append(cst.SimpleStatementLine(body=[ann_assign]))

        if not new_body or (
            len(new_body) == 1
            and isinstance(new_body[0], cst.SimpleStatementLine)
            and isinstance(new_body[0].body[0], cst.Expr)
        ):
            new_body.append(cst.SimpleStatementLine(body=[cst.Pass()]))

        # Set base class to NamedTuple
        base = cst.Arg(value=cst.Name("NamedTuple"))

        # Remove all decorators
        self.converted = True
        return updated_node.with_changes(
            decorators=[],
            bases=[base],
            body=updated_node.body.with_changes(body=new_body),
        )
