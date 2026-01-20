"""
Code generation utilities.

This package provides utilities for generating common Python code patterns
such as dunder methods, class conversions, and protocol extraction.
"""
from __future__ import annotations

from .dunder import (
    DunderGenerator,
    GenerateEqTransformer,
    GenerateHashTransformer,
    GenerateInitTransformer,
    GenerateReprTransformer,
)
from .conversions import (
    ConvertFromDataclassTransformer,
    ConvertToDataclassTransformer,
    ConvertToNamedTupleTransformer,
    ConvertToTypedDictTransformer,
)
from .protocol import (
    ExtractAbstractBaseTransformer,
    ExtractProtocolTransformer,
)
from .properties import (
    AddPropertyTransformer,
    ConvertAttributeToPropertyTransformer,
)
from .inheritance import (
    AddBaseClassTransformer,
    AddMixinTransformer,
    RemoveBaseClassTransformer,
)
from .tests import (
    AddPytestFixtureTransformer,
    DoctestExtractor,
    FunctionSignature,
    SignatureExtractor,
    TestCase,
    TestGenerator,
    UnittestToPytestConverter,
    extract_class_signatures,
    extract_doctests,
    extract_function_signature,
)

__all__ = [
    # Dunder generation
    "DunderGenerator",
    "GenerateEqTransformer",
    "GenerateHashTransformer",
    "GenerateInitTransformer",
    "GenerateReprTransformer",
    # Class conversions
    "ConvertFromDataclassTransformer",
    "ConvertToDataclassTransformer",
    "ConvertToNamedTupleTransformer",
    "ConvertToTypedDictTransformer",
    # Protocol extraction
    "ExtractAbstractBaseTransformer",
    "ExtractProtocolTransformer",
    # Properties
    "AddPropertyTransformer",
    "ConvertAttributeToPropertyTransformer",
    # Inheritance
    "AddBaseClassTransformer",
    "AddMixinTransformer",
    "RemoveBaseClassTransformer",
    # Test generation
    "AddPytestFixtureTransformer",
    "DoctestExtractor",
    "FunctionSignature",
    "SignatureExtractor",
    "TestCase",
    "TestGenerator",
    "UnittestToPytestConverter",
    "extract_class_signatures",
    "extract_doctests",
    "extract_function_signature",
]
