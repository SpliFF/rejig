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
# Generate all at once
cls.generate_dunders(["__init__", "__repr__", "__eq__", "__hash__"])

# Or use the shorthand
cls.generate_common_dunders()
```

### Customization Options

```python
cls.generate_init(
    include_super=True,           # Call super().__init__()
    include_defaults=True,        # Include default values
    optional_last=True,           # Put optional params last
    use_dataclass_style=False,    # Don't use field()
)

cls.generate_repr(
    include_private=False,        # Exclude _private attrs
    max_attrs=5,                  # Limit shown attributes
)

cls.generate_eq(
    compare_type=True,            # Include isinstance check
    use_slots=False,              # Don't assume __slots__
)
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

```python
cls.add_property(
    name="age",
    type_hint="int",
    getter_body="return self._age",
    setter_body="""
        if value < 0:
            raise ValueError("Age cannot be negative")
        self._age = value
    """,
)
```

### Read-Only Property

```python
cls.add_property(
    name="full_name",
    type_hint="str",
    getter_body="return f'{self.first_name} {self.last_name}'",
    setter=False,  # No setter, read-only
)
```

### Cached Property

```python
cls.add_cached_property(
    name="computed_value",
    type_hint="int",
    body="return expensive_computation(self.data)",
)

# Generates:
# @functools.cached_property
# def computed_value(self) -> int:
#     return expensive_computation(self.data)
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
    frozen=True,         # Immutable
    slots=True,          # Use __slots__
    kw_only=True,        # Keyword-only args
    order=True,          # Generate comparison methods
    eq=True,             # Generate __eq__
    repr_=True,          # Generate __repr__
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
abc = cls.extract_abc("AbstractDatabase")

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

### Generate Test Stubs

```python
from rejig import TestGenerator

generator = TestGenerator(rj)

# Generate tests for a function
func = rj.find_function("process_data")
test_code = generator.generate_test(func)

print(test_code)
# def test_process_data():
#     # Arrange
#     items = ...  # TODO: provide test data
#     limit = ...  # TODO: provide test data
#
#     # Act
#     result = process_data(items, limit)
#
#     # Assert
#     assert result is not None  # TODO: add assertions
```

### Generate Test File

```python
# Generate a complete test file for a module
test_file = generator.generate_test_file("src/utils.py")

with open("tests/test_utils.py", "w") as f:
    f.write(test_file)
```

### Generate Tests for Class

```python
cls = rj.find_class("UserService")
test_code = generator.generate_class_tests(cls)

# Generates:
# import pytest
# from myapp.services import UserService
#
# class TestUserService:
#     @pytest.fixture
#     def service(self):
#         return UserService()
#
#     def test_create_user(self, service):
#         # Arrange
#         name = ...
#         email = ...
#
#         # Act
#         result = service.create_user(name, email)
#
#         # Assert
#         assert result is not None
```

### Test Generation Options

```python
generator.generate_test(func,
    style="pytest",           # or "unittest"
    include_docstring=True,   # Add docstring to test
    include_arrange=True,     # Add Arrange section
    parametrize=True,         # Use @pytest.mark.parametrize
)
```

## unittest to pytest Conversion

### Convert Test Class

```python
from rejig import UnittestToPytestConverter

converter = UnittestToPytestConverter(rj)

# Convert a single test file
converter.convert_file("tests/test_utils.py")

# Before:
# import unittest
#
# class TestUtils(unittest.TestCase):
#     def setUp(self):
#         self.data = [1, 2, 3]
#
#     def test_sum(self):
#         self.assertEqual(sum(self.data), 6)
#
#     def test_len(self):
#         self.assertTrue(len(self.data) == 3)

# After:
# import pytest
#
# class TestUtils:
#     @pytest.fixture(autouse=True)
#     def setup(self):
#         self.data = [1, 2, 3]
#
#     def test_sum(self):
#         assert sum(self.data) == 6
#
#     def test_len(self):
#         assert len(self.data) == 3
```

### Batch Conversion

```python
# Convert all test files
converter.convert_all("tests/")
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

```python
from rejig import DoctestExtractor

extractor = DoctestExtractor(rj)

# Extract doctests from a module
tests = extractor.extract("src/utils.py")

# Generate pytest test file
test_code = extractor.to_pytest(tests)

print(test_code)
# def test_add_doctest_1():
#     \"\"\"From utils.add docstring.\"\"\"
#     assert add(2, 3) == 5
#
# def test_add_doctest_2():
#     assert add(-1, 1) == 0
```

## Batch Generation

### Generate for Multiple Classes

```python
# Generate dunders for all classes
for cls in rj.find_classes():
    if not cls.has_method("__repr__"):
        cls.generate_repr()

# Generate tests for all functions
generator = TestGenerator(rj)
for func in rj.find_functions():
    if not func.name.startswith("_"):
        test = generator.generate_test(func)
        # ... save to file
```

### Convert All Classes to Dataclasses

```python
# Find classes that look like data classes
for cls in rj.find_classes():
    # Has typed attributes but no complex methods
    if cls.has_typed_attributes() and not cls.has_complex_methods():
        cls.convert_to_dataclass()
```

## Common Patterns

### Modernize Data Classes

```python
rj = Rejig("src/")

# Find classes that should be dataclasses
for cls in rj.find_classes():
    methods = cls.find_methods()
    method_names = {m.name for m in methods}

    # Has __init__ that just assigns attributes
    if "__init__" in method_names:
        init = cls.find_method("__init__")
        if init.is_simple_assignment():
            cls.convert_to_dataclass()
```

### Add Missing Dunders

```python
for cls in rj.find_classes():
    # Add __repr__ if missing
    if not cls.has_method("__repr__"):
        cls.generate_repr()

    # Add __eq__ and __hash__ for value objects
    if cls.has_decorator("dataclass") or cls.has_typed_attributes():
        if not cls.has_method("__eq__"):
            cls.generate_eq()
        if not cls.has_method("__hash__"):
            cls.generate_hash()
```

### Generate Test Suite Skeleton

```python
from rejig import TestGenerator

rj = Rejig("src/myapp/")
generator = TestGenerator(rj)

# Generate tests for entire package
for file in rj.find_files():
    relative_path = file.path.relative_to(rj.root)
    test_path = Path("tests") / f"test_{relative_path}"

    if not test_path.exists():
        test_code = generator.generate_test_file(file.path)
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text(test_code)
        print(f"Generated: {test_path}")
```
