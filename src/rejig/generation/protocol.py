"""Protocol and abstract base class extraction."""
from __future__ import annotations

import libcst as cst


class ExtractProtocolTransformer(cst.CSTTransformer):
    """Extract a Protocol from a class definition.

    Creates a new Protocol class with specified method signatures and inserts
    it before the original class.

    Parameters
    ----------
    class_name : str
        Name of the class to extract from.
    protocol_name : str
        Name for the new Protocol class.
    methods : list[str] | None
        List of method names to include. If None, includes all public methods.
    """

    def __init__(
        self,
        class_name: str,
        protocol_name: str,
        methods: list[str] | None = None,
    ):
        super().__init__()
        self.class_name = class_name
        self.protocol_name = protocol_name
        self.methods = methods
        self.extracted = False
        self._protocol_node: cst.ClassDef | None = None

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value != self.class_name:
            return updated_node

        # Extract method signatures
        method_stubs: list[cst.BaseStatement] = []

        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef):
                method_name = stmt.name.value
                # Skip private methods unless explicitly requested
                if self.methods is not None:
                    if method_name not in self.methods:
                        continue
                else:
                    if method_name.startswith("_") and not method_name.startswith("__"):
                        continue

                # Create method stub with just '...' body
                stub_body = cst.IndentedBlock(
                    body=[cst.SimpleStatementLine(body=[cst.Expr(value=cst.Ellipsis())])]
                )

                # Keep decorators that are relevant to protocols (like @abstractmethod)
                protocol_decorators = []
                for dec in stmt.decorators:
                    if isinstance(dec.decorator, cst.Name):
                        if dec.decorator.value in ("abstractmethod", "property", "classmethod", "staticmethod"):
                            protocol_decorators.append(dec)

                method_stub = stmt.with_changes(
                    body=stub_body,
                    decorators=protocol_decorators,
                )
                method_stubs.append(method_stub)

        if not method_stubs:
            # No methods to extract
            return updated_node

        # Build Protocol class
        protocol_body = cst.IndentedBlock(body=method_stubs)

        self._protocol_node = cst.ClassDef(
            name=cst.Name(self.protocol_name),
            bases=[cst.Arg(value=cst.Name("Protocol"))],
            body=protocol_body,
            decorators=[],
        )

        self.extracted = True
        return updated_node

    def leave_Module(
        self,
        original_node: cst.Module,
        updated_node: cst.Module,
    ) -> cst.Module:
        if not self._protocol_node:
            return updated_node

        # Find the class and insert protocol before it
        new_body: list[cst.BaseStatement] = []
        for stmt in updated_node.body:
            if isinstance(stmt, cst.ClassDef) and stmt.name.value == self.class_name:
                # Insert protocol before the class
                new_body.append(self._protocol_node)
                new_body.append(cst.EmptyLine(whitespace=cst.SimpleWhitespace("")))
            new_body.append(stmt)

        return updated_node.with_changes(body=new_body)


class ExtractAbstractBaseTransformer(cst.CSTTransformer):
    """Extract an Abstract Base Class from a class definition.

    Creates a new ABC with abstract method signatures and inserts it before
    the original class, then makes the original class inherit from it.

    Parameters
    ----------
    class_name : str
        Name of the class to extract from.
    abc_name : str
        Name for the new ABC class.
    methods : list[str] | None
        List of method names to make abstract. If None, uses all public methods.
    """

    def __init__(
        self,
        class_name: str,
        abc_name: str,
        methods: list[str] | None = None,
    ):
        super().__init__()
        self.class_name = class_name
        self.abc_name = abc_name
        self.methods = methods
        self.extracted = False
        self._abc_node: cst.ClassDef | None = None

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value != self.class_name:
            return updated_node

        # Extract method signatures
        method_stubs: list[cst.BaseStatement] = []

        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef):
                method_name = stmt.name.value
                if self.methods is not None:
                    if method_name not in self.methods:
                        continue
                else:
                    if method_name.startswith("_") and not method_name.startswith("__"):
                        continue
                    # Skip dunder methods by default
                    if method_name.startswith("__") and method_name.endswith("__"):
                        if method_name not in ("__init__", "__call__"):
                            continue

                # Create abstract method stub
                stub_body = cst.IndentedBlock(
                    body=[cst.SimpleStatementLine(body=[cst.Expr(value=cst.Ellipsis())])]
                )

                # Add @abstractmethod decorator
                abstract_decorator = cst.Decorator(decorator=cst.Name("abstractmethod"))
                method_decorators = [abstract_decorator]

                # Keep property, classmethod, staticmethod decorators
                for dec in stmt.decorators:
                    if isinstance(dec.decorator, cst.Name):
                        if dec.decorator.value in ("property", "classmethod", "staticmethod"):
                            method_decorators.append(dec)

                method_stub = stmt.with_changes(
                    body=stub_body,
                    decorators=method_decorators,
                )
                method_stubs.append(method_stub)

        if not method_stubs:
            return updated_node

        # Build ABC class
        abc_body = cst.IndentedBlock(body=method_stubs)

        self._abc_node = cst.ClassDef(
            name=cst.Name(self.abc_name),
            bases=[cst.Arg(value=cst.Name("ABC"))],
            body=abc_body,
            decorators=[],
        )

        # Update original class to inherit from ABC
        new_bases = [cst.Arg(value=cst.Name(self.abc_name))] + list(updated_node.bases)

        self.extracted = True
        return updated_node.with_changes(bases=new_bases)

    def leave_Module(
        self,
        original_node: cst.Module,
        updated_node: cst.Module,
    ) -> cst.Module:
        if not self._abc_node:
            return updated_node

        # Find the class and insert ABC before it
        new_body: list[cst.BaseStatement] = []
        for stmt in updated_node.body:
            if isinstance(stmt, cst.ClassDef) and stmt.name.value == self.class_name:
                new_body.append(self._abc_node)
                new_body.append(cst.EmptyLine(whitespace=cst.SimpleWhitespace("")))
            new_body.append(stmt)

        return updated_node.with_changes(body=new_body)
