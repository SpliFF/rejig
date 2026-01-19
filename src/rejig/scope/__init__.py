"""
Scope classes for fluent API.

These classes represent scoped contexts (class, method, function) that
allow chaining operations on specific code elements.

Example
-------
>>> pym = Manipylate("src/")
>>> class_scope = pym.find_class("MyClass")
>>> method_scope = class_scope.find_method("my_method")
>>> method_scope.insert_statement("print('hello')")
"""
from __future__ import annotations

from .base import BaseScope
from .class_scope import ClassScope
from .function_scope import FunctionScope
from .method_scope import MethodScope

__all__ = [
    "BaseScope",
    "ClassScope",
    "FunctionScope",
    "MethodScope",
]
