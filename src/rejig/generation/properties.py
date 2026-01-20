"""Property generation and conversion for Python classes."""
from __future__ import annotations

import libcst as cst


class ConvertAttributeToPropertyTransformer(cst.CSTTransformer):
    """Convert a class attribute to a property with getter/setter.

    Parameters
    ----------
    class_name : str
        Name of the class to modify.
    attr_name : str
        Name of the attribute to convert.
    getter : bool
        If True, generate a getter property. Default True.
    setter : bool
        If True, generate a setter. Default True.
    private_prefix : str
        Prefix for the private backing attribute. Default "_".
    """

    def __init__(
        self,
        class_name: str,
        attr_name: str,
        getter: bool = True,
        setter: bool = True,
        private_prefix: str = "_",
    ):
        super().__init__()
        self.class_name = class_name
        self.attr_name = attr_name
        self.getter = getter
        self.setter = setter
        self.private_prefix = private_prefix
        self.converted = False
        self._type_hint: str | None = None
        self._default_value: str | None = None

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value != self.class_name:
            return updated_node

        new_body: list[cst.BaseStatement] = []
        found_attr = False
        property_methods: list[cst.BaseStatement] = []

        # Find and remove the attribute, save its type/default
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                skip = False
                for s in stmt.body:
                    if isinstance(s, cst.AnnAssign) and isinstance(s.target, cst.Name):
                        if s.target.value == self.attr_name:
                            found_attr = True
                            skip = True
                            self._type_hint = cst.parse_module("").code_for_node(
                                s.annotation.annotation
                            )
                            if s.value:
                                self._default_value = cst.parse_module("").code_for_node(s.value)
                            break
                    elif isinstance(s, cst.Assign):
                        for target in s.targets:
                            if isinstance(target.target, cst.Name) and target.target.value == self.attr_name:
                                found_attr = True
                                skip = True
                                self._default_value = cst.parse_module("").code_for_node(s.value)
                                break
                if not skip:
                    new_body.append(stmt)
            else:
                new_body.append(stmt)

        if not found_attr:
            return updated_node

        # Generate private attribute
        private_name = f"{self.private_prefix}{self.attr_name}"
        if self._type_hint:
            if self._default_value:
                private_attr = cst.SimpleStatementLine(
                    body=[
                        cst.AnnAssign(
                            target=cst.Name(private_name),
                            annotation=cst.Annotation(annotation=cst.parse_expression(self._type_hint)),
                            value=cst.parse_expression(self._default_value),
                        )
                    ]
                )
            else:
                private_attr = cst.SimpleStatementLine(
                    body=[
                        cst.AnnAssign(
                            target=cst.Name(private_name),
                            annotation=cst.Annotation(annotation=cst.parse_expression(self._type_hint)),
                            value=None,
                        )
                    ]
                )
        else:
            if self._default_value:
                private_attr = cst.SimpleStatementLine(
                    body=[
                        cst.Assign(
                            targets=[cst.AssignTarget(target=cst.Name(private_name))],
                            value=cst.parse_expression(self._default_value),
                        )
                    ]
                )
            else:
                private_attr = cst.SimpleStatementLine(
                    body=[
                        cst.AnnAssign(
                            target=cst.Name(private_name),
                            annotation=cst.Annotation(annotation=cst.Name("Any")),
                            value=None,
                        )
                    ]
                )

        # Generate getter property
        if self.getter:
            return_annotation = ""
            if self._type_hint:
                return_annotation = f" -> {self._type_hint}"
            getter_code = f"""@property
def {self.attr_name}(self){return_annotation}:
    return self.{private_name}"""
            property_methods.append(cst.parse_statement(getter_code))

        # Generate setter
        if self.setter:
            param_annotation = ""
            if self._type_hint:
                param_annotation = f": {self._type_hint}"
            setter_code = f"""@{self.attr_name}.setter
def {self.attr_name}(self, value{param_annotation}) -> None:
    self.{private_name} = value"""
            property_methods.append(cst.parse_statement(setter_code))

        # Insert private attribute at the beginning (after docstring)
        insert_idx = 0
        if new_body and isinstance(new_body[0], cst.SimpleStatementLine):
            if len(new_body[0].body) == 1 and isinstance(new_body[0].body[0], cst.Expr):
                expr = new_body[0].body[0].value
                if isinstance(expr, (cst.SimpleString, cst.ConcatenatedString, cst.FormattedString)):
                    insert_idx = 1

        new_body.insert(insert_idx, private_attr)

        # Add property methods at the end
        new_body.extend(property_methods)

        self.converted = True
        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=new_body)
        )


class AddPropertyTransformer(cst.CSTTransformer):
    """Add a property to a class.

    Parameters
    ----------
    class_name : str
        Name of the class to modify.
    prop_name : str
        Name of the property.
    getter_body : str
        Body of the getter (a return statement or expression).
    setter_body : str | None
        Body of the setter. If None, property is read-only.
    return_type : str | None
        Return type annotation for the getter.
    """

    def __init__(
        self,
        class_name: str,
        prop_name: str,
        getter_body: str,
        setter_body: str | None = None,
        return_type: str | None = None,
    ):
        super().__init__()
        self.class_name = class_name
        self.prop_name = prop_name
        self.getter_body = getter_body
        self.setter_body = setter_body
        self.return_type = return_type
        self.added = False

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value != self.class_name:
            return updated_node

        # Check if property already exists
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.prop_name:
                return updated_node

        new_body = list(updated_node.body.body)

        # Build getter
        return_annotation = ""
        if self.return_type:
            return_annotation = f" -> {self.return_type}"

        # Handle body - if it doesn't start with 'return', wrap it
        getter_body = self.getter_body.strip()
        if not getter_body.startswith("return "):
            getter_body = f"return {getter_body}"

        getter_code = f"""@property
def {self.prop_name}(self){return_annotation}:
    {getter_body}"""
        new_body.append(cst.parse_statement(getter_code))

        # Build setter if provided
        if self.setter_body:
            setter_code = f"""@{self.prop_name}.setter
def {self.prop_name}(self, value) -> None:
    {self.setter_body}"""
            new_body.append(cst.parse_statement(setter_code))

        self.added = True
        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=new_body)
        )
