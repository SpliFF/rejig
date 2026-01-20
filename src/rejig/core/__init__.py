"""
Core module.

Example
-------
>>> from rejig import Rejig
>>>
>>> # Initialize with a directory or glob pattern
>>> rj = Rejig("src/")
>>>
>>> # Find a class and add an attribute
>>> rj.find_class("MyClass").add_attribute("new_attr", "str | None", "None")
>>>
>>> # Chain operations on methods
>>> rj.find_class("MyClass").find_method("my_method").insert_statement("print('hello')")
"""
from __future__ import annotations

from .rejig import Rejig
from .results import BatchResult, ErrorResult, Result
from .transaction import Transaction

__all__ = [
    "Rejig",
    "Result",
    "ErrorResult",
    "BatchResult",
    "Transaction",
]
