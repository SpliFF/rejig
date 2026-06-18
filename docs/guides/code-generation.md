# Code Generation

Rejig provides tools for generating boilerplate code: dunder methods, properties, test stubs, and class conversions.

## Dunder Method Generation

Generate common special methods for classes.

### Generate `__init__`

```python
from rejig import Rejig

rj = Rejig("src/")
cls = rj.find_class("Person")

# Generate __init__ from class attributes
cls.generate_init()

# Before:
# class Person:
#     name: str
#     age: int
#     email: str | None

# After:
# class Person:
#     name: str
#     age: int
#     email: str | None
#
#     def __init__(self, name: str, age: int, email: str | None = None) -> None:
#         self.name = name
#         self.age = age
#         self.email = email
```

### Generate `__repr__`

```python
cls.generate_repr()

# Generates:
# def __repr__(self) -> str:
#     return f"Person(name={self.name!r}, age={self.age!r}, email={self.email!r})"
```

### Generate `__eq__`

```python
cls.generate_eq()

# Generates:
# def __eq__(self, other: object) -> bool:
#     if not isinstance(other, Person):
#         return NotImplemented
#     return (self.name, self.age, self.email) == (other.name, other.age, other.email)
```

### Generate `__hash__`

```python
cls.generate_hash()

# Generates:
# def __hash__(self) -> int:
#     return hash((self.name, self.age, self.email))
```

### Generate All Common Dunders

```python
# Generate __init__, __repr__, __eq__, and __hash__ at once
cls.generate_all_dunders()
```

### Overwriting Existing Dunders

By default, generation skips a dunder that already exists. Pass
`overwrite=True` to replace it:

```python
cls.generate_init(overwrite=True)
cls.generate_repr(overwrite=True)
cls.generate_eq(overwrite=True)
cls.generate_hash(overwrite=True)
cls.generate_all_dunders(overwrite=True)
```

## Property Generation

### Convert Attribute to Property

```python
cls = rj.find_class("User")

# Convert an attribute to a property with getter/setter
cls.convert_attribute_to_property("email")

# Before:
# class User:
#     email: str

# After:
# class User:
#     _email: str
#
#     @property
#     def email(self) -> str:
#         return self._email
#
#     @email.setter
#     def email(self, value: str) -> None:
#         self._email = value
```

### Add Property with Validation

`add_property` takes the getter body as a string, an optional setter body, and
an optional return type:

```python
cls.add_property(
    "age",
    getter="self._age",
    setter="""
        if value < 0:
            raise ValueError("Age cannot be negative")
        self._age = value
    """,
    return_type="int",
)
```

### Read-Only Property

```python
cls.add_property(
    "full_name",
    getter="f'{self.first_name} {self.last_name}'",
    return_type="str",
)  # No setter argument means the property is read-only
```

## Class Conversions

### Convert to Dataclass

```python
cls = rj.find_class("Config")
cls.convert_to_dataclass()

# Before:
# class Config:
#     host: str
#     port: int
#     debug: bool
#
#     def __init__(self, host: str, port: int, debug: bool = False):
#         self.host = host
#         self.port = port
#         self.debug = debug

# After:
# from dataclasses import dataclass
#
# @dataclass
# class Config:
#     host: str
#     port: int
#     debug: bool = False
```

### Dataclass Options

```python
cls.convert_to_dataclass(
    frozen=True,         # Immutable (frozen=True)
    slots=True,          # Use __slots__ (Python 3.10+)
)
```

### Convert to NamedTuple

```python
cls.convert_to_named_tuple()

# Before:
# class Point:
#     x: int
#     y: int

# After:
# from typing import NamedTuple
#
# class Point(NamedTuple):
#     x: int
#     y: int
```

### Convert to TypedDict

```python
cls.convert_to_typed_dict()

# Before:
# class UserData:
#     name: str
#     age: int
#     email: str | None

# After:
# from typing import TypedDict
#
# class UserData(TypedDict):
#     name: str
#     age: int
#     email: str | None
```

### Convert from Dataclass

```python
# Convert back to regular class
cls.convert_from_dataclass()
```

## Protocol and ABC Extraction

### Extract Protocol

```python
cls = rj.find_class("DatabaseConnection")

# Extract a Protocol from the class's public interface
protocol = cls.extract_protocol("DatabaseProtocol")

# Creates:
# from typing import Protocol
#
# class DatabaseProtocol(Protocol):
#     def connect(self) -> None: ...
#     def execute(self, query: str) -> list[dict]: ...
#     def close(self) -> None: ...
```

### Extract Abstract Base Class

```python
result = cls.extract_abstract_base("AbstractDatabase")

# Creates:
# from abc import ABC, abstractmethod
#
# class AbstractDatabase(ABC):
#     @abstractmethod
#     def connect(self) -> None: ...
#
#     @abstractmethod
#     def execute(self, query: str) -> list[dict]: ...
#
#     @abstractmethod
#     def close(self) -> None: ...
```

## Inheritance Management

### Add Base Class

```python
cls = rj.find_class("MyModel")
cls.add_base_class("BaseModel")

# Before:
# class MyModel:

# After:
# class MyModel(BaseModel):
```

### Add Mixin

```python
cls.add_mixin("TimestampMixin")

# Before:
# class MyModel(BaseModel):

# After:
# class MyModel(TimestampMixin, BaseModel):
```

### Remove Base Class

```python
cls.remove_base_class("DeprecatedMixin")
```

## Test Generation

Test stubs are generated through the target API. Each method returns a
`Result`; the generated code is also available in `result.data`.

### Generate a Test Stub for a Function

```python
func = rj.find_function("process_data")

# Writes tests/test_<module>.py with a stub for the function
result = func.generate_test_stub()
print(result.data)
# def test_process_data():
#     # Arrange
#     items = []
#
#     # Act
#     result = process_data(items)
#
#     # Assert
#     assert result is not None  # TODO: add specific assertions
```

### Generate a Test File for a Class

```python
cls = rj.find_class("UserService")

# Write a complete pytest test file with stubs for all public methods
result = cls.generate_test_file("tests/test_user_service.py")

# Or write into the default tests/ directory mirroring the source layout
cls.generate_test_stub()
```

### Generate a Test for a Single Method

```python
method = rj.find_class("UserService").find_method("create_user")

# Simple stub
method.generate_test()

# Parameterized test from explicit cases
method.generate_test(
    test_cases=[
        {"input": {"data": "valid"}, "expected": True},
        {"input": {"data": ""}, "expected": False},
    ]
)
```

### Generate a Test Class Scaffold

```python
# Create a standalone test class (no source class required)
rj.generate_test_class("MyClass", include_setup=True)
```

### Low-Level Generator

For finer control, use `TestGenerator` from `rejig.generation` directly. It
works on `FunctionSignature` objects (extracted via `SignatureExtractor`)
rather than targets:

```python
from rejig.generation import TestGenerator

generator = TestGenerator()
# generator.generate_function_test_stub(signature)
# generator.generate_class_test_file(class_name, method_signatures)
# generator.generate_parameterized_test(signature, test_cases)
```

## unittest to pytest Conversion

`UnittestToPytestConverter` is a LibCST transformer that rewrites
`self.assertX(...)` calls into plain `assert` statements. Apply it with
`Rejig.transform_file`:

```python
from rejig.generation import UnittestToPytestConverter

rj.transform_file(
    rj.root / "tests/test_utils.py",
    UnittestToPytestConverter(),
)

# Before:  self.assertEqual(sum(self.data), 6)
# After:   assert sum(self.data) == 6
```

### Batch Conversion

```python
# Convert every test file in the working set
for file in rj.find_files("**/test_*.py"):
    rj.transform_file(file.path, UnittestToPytestConverter())
```

### Assertion Conversions

The converter handles these assertion patterns:

| unittest | pytest |
|----------|--------|
| `self.assertEqual(a, b)` | `assert a == b` |
| `self.assertNotEqual(a, b)` | `assert a != b` |
| `self.assertTrue(x)` | `assert x` |
| `self.assertFalse(x)` | `assert not x` |
| `self.assertIs(a, b)` | `assert a is b` |
| `self.assertIsNone(x)` | `assert x is None` |
| `self.assertIn(a, b)` | `assert a in b` |
| `self.assertRaises(E)` | `pytest.raises(E)` |
| `self.assertAlmostEqual(a, b)` | `assert a == pytest.approx(b)` |

## Doctest Extraction

### Extract Doctests to pytest

Convert the doctest examples in a function's docstring into pytest tests:

```python
func = rj.find_function("add")

result = func.generate_tests_from_doctest()
print(result.data)
# def test_add_doctest_1():
#     """Test from doctest example."""
#     result = add(2, 3)
#     assert result == 5
#
# def test_add_doctest_2():
#     """Test from doctest example."""
#     result = add(-1, 1)
#     assert result == 0

# Or write to a specific file
func.generate_tests_from_doctest("tests/test_doctests.py")
```

## Batch Generation

### Generate for Multiple Classes

Generation methods skip elements that already exist (unless `overwrite=True`),
so they are safe to call across every class:

```python
# Generate __repr__ for all classes that lack one
for cls in rj.find_classes():
    cls.generate_repr()

# Generate test stubs for all public functions
for func in rj.find_functions():
    if not func.name.startswith("_"):
        func.generate_test_stub()
```

### Add Missing Dunders

```python
# generate_* is a no-op when the dunder already exists
for cls in rj.find_classes():
    cls.generate_repr()
    cls.generate_eq()
    cls.generate_hash()

    # Or all at once
    cls.generate_all_dunders()
```

## Common Patterns

### Generate a Test Suite Skeleton

```python
rj = Rejig("src/myapp/")

# One test file per class, in the default tests/ directory
for cls in rj.find_classes():
    cls.generate_test_stub()

# Only for classes that don't yet have a test class
for cls in rj.find_classes_without_tests():
    cls.generate_test_file(f"tests/test_{cls.name.lower()}.py")
```
