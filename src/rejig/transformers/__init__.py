"""
LibCST-based code transformers.

This package contains all the low-level CST transformers used by the
higher-level scope classes.
"""
from __future__ import annotations

from .add_class_attribute import AddClassAttribute
from .add_first_parameter import AddFirstParameter
from .add_method_decorator import AddMethodDecorator
from .insert_at_match import InsertAtMatch
from .insert_at_method_start import InsertAtMethodStart
from .remove_class_attribute import RemoveClassAttribute
from .remove_decorator import RemoveDecorator
from .remove_method_decorator import RemoveMethodDecorator
from .remove_module_level_assignment import RemoveModuleLevelAssignment
from .rename_class import RenameClass
from .rename_method import RenameMethod
from .replace_identifier import ReplaceIdentifier
from .static_to_class_method import StaticToClassMethod

__all__ = [
    "AddClassAttribute",
    "AddFirstParameter",
    "AddMethodDecorator",
    "InsertAtMatch",
    "InsertAtMethodStart",
    "RemoveClassAttribute",
    "RemoveDecorator",
    "RemoveMethodDecorator",
    "RemoveModuleLevelAssignment",
    "RenameClass",
    "RenameMethod",
    "ReplaceIdentifier",
    "StaticToClassMethod",
]
