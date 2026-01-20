"""
LibCST-based code transformers.

This package contains all the low-level CST transformers used by the
higher-level target classes.
"""
from __future__ import annotations

from .add_class_attribute import AddClassAttribute
from .add_class_decorator import AddClassDecorator
from .add_first_parameter import AddFirstParameter
from .add_function_decorator import AddFunctionDecorator
from .add_method_decorator import AddMethodDecorator
from .add_parameter import AddParameter
from .infer_type_hints import InferTypeHints
from .insert_at_match import InsertAtMatch
from .insert_at_method_end import InsertAtMethodEnd
from .insert_at_method_start import InsertAtMethodStart
from .remove_class_attribute import RemoveClassAttribute
from .remove_decorator import RemoveDecorator
from .remove_method_decorator import RemoveMethodDecorator
from .remove_module_level_assignment import RemoveModuleLevelAssignment
from .remove_type_hints import RemoveTypeHints
from .rename_class import RenameClass
from .rename_method import RenameMethod
from .replace_identifier import ReplaceIdentifier
from .set_parameter_type import SetParameterType
from .set_return_type import SetReturnType
from .static_to_class_method import StaticToClassMethod

__all__ = [
    "AddClassAttribute",
    "AddClassDecorator",
    "AddFirstParameter",
    "AddFunctionDecorator",
    "AddMethodDecorator",
    "AddParameter",
    "InferTypeHints",
    "InsertAtMatch",
    "InsertAtMethodEnd",
    "InsertAtMethodStart",
    "RemoveClassAttribute",
    "RemoveDecorator",
    "RemoveMethodDecorator",
    "RemoveModuleLevelAssignment",
    "RemoveTypeHints",
    "RenameClass",
    "RenameMethod",
    "ReplaceIdentifier",
    "SetParameterType",
    "SetReturnType",
    "StaticToClassMethod",
]
