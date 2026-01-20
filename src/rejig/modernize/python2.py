"""Python 2 compatibility removal transformers.

Removes Python 2 compatibility code:
- `from __future__ import print_function, division, absolute_import`
- `# -*- coding: utf-8 -*-` comments
- `super(ClassName, self)` → `super()`
- `six` library usage
- `u"string"` unicode prefixes
- `object` as only base class
"""
from __future__ import annotations

import libcst as cst


class RemovePython2CompatTransformer(cst.CSTTransformer):
    """Remove Python 2 compatibility code.

    Removes:
    - __future__ imports (except annotations)
    - super(ClassName, self) → super()
    - u"string" prefixes → "string"
    - Unnecessary (object) base class when it's the only base
    """

    # __future__ imports that are now default in Python 3
    PYTHON2_FUTURE_IMPORTS = {
        "print_function",
        "division",
        "absolute_import",
        "unicode_literals",
        "generator_stop",
        "nested_scopes",
        "generators",
        "with_statement",
    }

    def __init__(self) -> None:
        super().__init__()
        self.changed = False
        self._current_class: str | None = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Track current class name for super() conversion."""
        self._current_class = node.name.value
        return True

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Remove unnecessary (object) base class and reset class tracking."""
        self._current_class = None

        # Check if the only base class is `object`
        if len(updated_node.bases) == 1:
            base = updated_node.bases[0]
            if isinstance(base.value, cst.Name) and base.value.value == "object":
                # Remove the base class
                self.changed = True
                return updated_node.with_changes(
                    bases=[],
                    lpar=cst.MaybeSentinel.DEFAULT,
                    rpar=cst.MaybeSentinel.DEFAULT,
                )

        return updated_node

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom | cst.RemovalSentinel:
        """Remove Python 2 __future__ imports."""
        if not isinstance(updated_node.module, cst.Attribute):
            if isinstance(updated_node.module, cst.Name):
                if updated_node.module.value == "__future__":
                    return self._filter_future_imports(updated_node)
        return updated_node

    def _filter_future_imports(
        self, node: cst.ImportFrom
    ) -> cst.ImportFrom | cst.RemovalSentinel:
        """Filter out Python 2 __future__ imports, keeping annotations."""
        if isinstance(node.names, cst.ImportStar):
            return node

        names_to_keep: list[cst.ImportAlias] = []
        for name in node.names:
            if isinstance(name.name, cst.Name):
                if name.name.value not in self.PYTHON2_FUTURE_IMPORTS:
                    names_to_keep.append(name)
            else:
                names_to_keep.append(name)

        if not names_to_keep:
            self.changed = True
            return cst.RemovalSentinel.REMOVE

        if len(names_to_keep) < len(node.names):
            self.changed = True
            return node.with_changes(names=names_to_keep)

        return node

    def leave_Call(
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        """Convert super(ClassName, self) to super()."""
        if not isinstance(updated_node.func, cst.Name):
            return updated_node

        if updated_node.func.value != "super":
            return updated_node

        # Check for super(ClassName, self) pattern
        args = updated_node.args
        if len(args) != 2:
            return updated_node

        # First arg should be the class name, second should be self
        first_arg = args[0].value
        second_arg = args[1].value

        if not isinstance(first_arg, cst.Name):
            return updated_node
        if not isinstance(second_arg, cst.Name):
            return updated_node

        # Check if second arg is self or cls
        if second_arg.value not in ("self", "cls"):
            return updated_node

        # Convert to super()
        self.changed = True
        return updated_node.with_changes(args=[])

    def leave_SimpleString(
        self, original_node: cst.SimpleString, updated_node: cst.SimpleString
    ) -> cst.SimpleString:
        """Remove u"" unicode string prefixes."""
        value = updated_node.value
        if value.startswith(("u'", 'u"', "U'", 'U"')):
            self.changed = True
            return updated_node.with_changes(value=value[1:])
        if value.startswith(("ur'", 'ur"', "Ur'", 'Ur"', "uR'", 'uR"', "UR'", 'UR"')):
            self.changed = True
            return updated_node.with_changes(value="r" + value[2:])
        return updated_node

    def leave_Comment(
        self, original_node: cst.Comment, updated_node: cst.Comment
    ) -> cst.Comment | cst.RemovalSentinel:
        """Remove coding declaration comments."""
        comment = updated_node.value
        # Match: # -*- coding: utf-8 -*-  or  # coding: utf-8  or  # vim: set fileencoding=utf-8 :
        if "coding" in comment.lower() and ("utf-8" in comment.lower() or "utf8" in comment.lower()):
            self.changed = True
            return cst.RemovalSentinel.REMOVE
        return updated_node


class AddFutureAnnotationsTransformer(cst.CSTTransformer):
    """Add `from __future__ import annotations` to a module."""

    def __init__(self) -> None:
        super().__init__()
        self.added = False
        self._has_future_annotations = False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool:
        """Check if future annotations import already exists."""
        if isinstance(node.module, cst.Name) and node.module.value == "__future__":
            if isinstance(node.names, cst.ImportStar):
                self._has_future_annotations = True
                return False

            for name in node.names:
                if isinstance(name.name, cst.Name) and name.name.value == "annotations":
                    self._has_future_annotations = True
                    return False
        return False

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add the import at the beginning of the module."""
        if self._has_future_annotations:
            return updated_node

        # Create the import statement
        future_import = cst.SimpleStatementLine(
            body=[
                cst.ImportFrom(
                    module=cst.Name("__future__"),
                    names=[cst.ImportAlias(name=cst.Name("annotations"))],
                )
            ],
        )

        # Find where to insert (after any existing __future__ imports or docstring)
        insert_idx = 0
        body = list(updated_node.body)

        # Skip module docstring
        if body and isinstance(body[0], cst.SimpleStatementLine):
            if body[0].body and isinstance(body[0].body[0], cst.Expr):
                if isinstance(body[0].body[0].value, (cst.SimpleString, cst.ConcatenatedString)):
                    insert_idx = 1

        # Skip existing __future__ imports and add to them
        while insert_idx < len(body):
            stmt = body[insert_idx]
            if isinstance(stmt, cst.SimpleStatementLine):
                for item in stmt.body:
                    if isinstance(item, cst.ImportFrom):
                        if isinstance(item.module, cst.Name) and item.module.value == "__future__":
                            # Add annotations to existing __future__ import
                            if isinstance(item.names, (list, tuple)):
                                new_names = list(item.names) + [
                                    cst.ImportAlias(
                                        name=cst.Name("annotations"),
                                        comma=cst.MaybeSentinel.DEFAULT,
                                    )
                                ]
                                new_import = item.with_changes(names=new_names)
                                new_stmt = stmt.with_changes(
                                    body=[new_import] + list(stmt.body[1:])
                                )
                                body[insert_idx] = new_stmt
                                self.added = True
                                return updated_node.with_changes(body=body)
            break

        # Insert new import
        body.insert(insert_idx, future_import)
        self.added = True
        return updated_node.with_changes(body=body)


class RemoveSixUsageTransformer(cst.CSTTransformer):
    """Remove `six` library compatibility usage.

    Converts:
    - six.text_type → str
    - six.binary_type → bytes
    - six.string_types → str (in isinstance checks)
    - six.moves.range → range
    - six.PY2, six.PY3 → True/False
    - @six.add_metaclass(Meta) → class Foo(metaclass=Meta)
    """

    SIX_TYPE_MAPPINGS = {
        "text_type": "str",
        "binary_type": "bytes",
        "integer_types": "int",
        "string_types": "str",
    }

    SIX_MOVES_MAPPINGS = {
        "range": "range",
        "map": "map",
        "filter": "filter",
        "zip": "zip",
        "input": "input",
        "intern": "sys.intern",
        "reduce": "functools.reduce",
        "reload_module": "importlib.reload",
    }

    def __init__(self) -> None:
        super().__init__()
        self.changed = False
        self._six_imported = False
        self._six_aliases: dict[str, str] = {}

    def visit_Import(self, node: cst.Import) -> bool:
        """Track if six is imported."""
        for name in node.names:
            if isinstance(name, cst.ImportAlias):
                if isinstance(name.name, cst.Name) and name.name.value == "six":
                    self._six_imported = True
        return False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool:
        """Track six imports."""
        if isinstance(node.module, cst.Name) and node.module.value == "six":
            self._six_imported = True
            if isinstance(node.names, (list, tuple)):
                for name in node.names:
                    if isinstance(name, cst.ImportAlias) and isinstance(name.name, cst.Name):
                        alias_name = name.asname.name.value if name.asname else name.name.value
                        self._six_aliases[alias_name] = name.name.value
        return False

    def leave_Attribute(
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.BaseExpression:
        """Convert six.X to Python 3 equivalents."""
        if isinstance(updated_node.value, cst.Name):
            if updated_node.value.value == "six":
                attr_name = updated_node.attr.value

                # six.text_type → str, etc.
                if attr_name in self.SIX_TYPE_MAPPINGS:
                    self.changed = True
                    return cst.Name(self.SIX_TYPE_MAPPINGS[attr_name])

                # six.PY2 → False, six.PY3 → True
                if attr_name == "PY2":
                    self.changed = True
                    return cst.Name("False")
                if attr_name == "PY3":
                    self.changed = True
                    return cst.Name("True")

        # six.moves.range → range
        if isinstance(updated_node.value, cst.Attribute):
            inner = updated_node.value
            if isinstance(inner.value, cst.Name) and inner.value.value == "six":
                if inner.attr.value == "moves":
                    attr_name = updated_node.attr.value
                    if attr_name in self.SIX_MOVES_MAPPINGS:
                        self.changed = True
                        return cst.Name(self.SIX_MOVES_MAPPINGS[attr_name])

        return updated_node
