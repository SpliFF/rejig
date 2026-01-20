"""Inheritance operations for Python classes."""
from __future__ import annotations

import libcst as cst


class AddBaseClassTransformer(cst.CSTTransformer):
    """Add a base class to a class definition.

    Parameters
    ----------
    class_name : str
        Name of the class to modify.
    base_class : str
        Name of the base class to add. Can include module path (e.g., "abc.ABC").
    position : str
        Where to add the base class: "first", "last". Default "last".
    """

    def __init__(
        self,
        class_name: str,
        base_class: str,
        position: str = "last",
    ):
        super().__init__()
        self.class_name = class_name
        self.base_class = base_class
        self.position = position
        self.added = False

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value != self.class_name:
            return updated_node

        # Check if base class already exists
        for base in updated_node.bases:
            base_code = cst.parse_module("").code_for_node(base.value)
            if base_code == self.base_class:
                return updated_node

        # Create new base
        new_base = cst.Arg(value=cst.parse_expression(self.base_class))

        # Add to bases
        if self.position == "first":
            new_bases = [new_base] + list(updated_node.bases)
        else:
            new_bases = list(updated_node.bases) + [new_base]

        self.added = True
        return updated_node.with_changes(bases=new_bases)


class RemoveBaseClassTransformer(cst.CSTTransformer):
    """Remove a base class from a class definition.

    Parameters
    ----------
    class_name : str
        Name of the class to modify.
    base_class : str
        Name of the base class to remove.
    """

    def __init__(self, class_name: str, base_class: str):
        super().__init__()
        self.class_name = class_name
        self.base_class = base_class
        self.removed = False

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value != self.class_name:
            return updated_node

        new_bases = []
        for base in updated_node.bases:
            base_code = cst.parse_module("").code_for_node(base.value)
            if base_code != self.base_class:
                new_bases.append(base)
            else:
                self.removed = True

        if not self.removed:
            return updated_node

        return updated_node.with_changes(bases=new_bases)


class AddMixinTransformer(cst.CSTTransformer):
    """Add a mixin class to a class definition.

    Mixins are always added at the beginning of the base class list
    (before other base classes) following Python MRO conventions.

    Parameters
    ----------
    class_name : str
        Name of the class to modify.
    mixin_class : str
        Name of the mixin class to add.
    """

    def __init__(self, class_name: str, mixin_class: str):
        super().__init__()
        self.class_name = class_name
        self.mixin_class = mixin_class
        self.added = False

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value != self.class_name:
            return updated_node

        # Check if mixin already exists
        for base in updated_node.bases:
            base_code = cst.parse_module("").code_for_node(base.value)
            if base_code == self.mixin_class:
                return updated_node

        # Create new mixin base
        new_mixin = cst.Arg(value=cst.parse_expression(self.mixin_class))

        # Add mixin at the beginning (before other bases)
        new_bases = [new_mixin] + list(updated_node.bases)

        self.added = True
        return updated_node.with_changes(bases=new_bases)
