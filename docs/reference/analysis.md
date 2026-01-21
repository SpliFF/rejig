# Analysis Reference

Reference for code analysis types and findings.

## AnalysisType Enum

Types of analysis issues detected.

### Complexity Issues

| Type | Description | Default Threshold |
|------|-------------|-------------------|
| `HIGH_CYCLOMATIC_COMPLEXITY` | Function has too many branches | 10 |
| `DEEP_NESTING` | Code nested too deeply | 4 levels |
| `LONG_FUNCTION` | Function has too many lines | 50 lines |
| `LONG_CLASS` | Class has too many lines/methods | 300 lines |
| `TOO_MANY_PARAMETERS` | Function has too many parameters | 5 |
| `TOO_MANY_BRANCHES` | Too many if/elif branches | 8 |
| `TOO_MANY_RETURNS` | Function has too many return statements | 4 |

### Documentation Issues

| Type | Description |
|------|-------------|
| `MISSING_TYPE_HINT` | Function lacks type annotations |
| `MISSING_DOCSTRING` | Public function/class lacks docstring |

### Code Quality Issues

| Type | Description |
|------|-------------|
| `BARE_EXCEPT` | Catching all exceptions (`except:`) |
| `HARDCODED_STRING` | Magic string that should be a constant |
| `MAGIC_NUMBER` | Numeric literal that should be named |
| `TODO_COMMENT` | TODO/FIXME/XXX/HACK comment in code |

### Dead Code Issues

| Type | Description |
|------|-------------|
| `UNUSED_FUNCTION` | Function is never called |
| `UNUSED_CLASS` | Class is never instantiated or subclassed |
| `UNUSED_VARIABLE` | Variable is assigned but never used |
| `UNUSED_IMPORT` | Import is never used |
| `UNREACHABLE_CODE` | Code after return/raise/break |

## AnalysisFinding

Dataclass representing an analysis finding.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `type` | `AnalysisType` | Type of issue |
| `file_path` | `Path` | File containing the issue |
| `line_number` | `int` | Line number (1-indexed) |
| `name` | `str` | Name of the element |
| `message` | `str` | Human-readable description |
| `severity` | `str` | "high", "medium", or "low" |
| `value` | `Any` | Actual value (e.g., complexity score) |
| `threshold` | `Any` | Threshold that was exceeded |
| `context` | `dict` | Additional context |

## AnalysisTarget

Target wrapping an analysis finding.

### Properties

All properties from `AnalysisFinding` plus:

| Property | Type | Description |
|----------|------|-------------|
| `finding` | `AnalysisFinding` | The underlying finding |

### Navigation Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `to_file_target()` | `FileTarget` | Get file containing issue |
| `to_line_target()` | `LineTarget` | Get line with issue |
| `exists()` | `bool` | Always True for valid findings |

## AnalysisTargetList

List of analysis findings with filtering and aggregation.

### Filtering

| Method | Description |
|--------|-------------|
| `by_type(type)` | Filter by single type |
| `by_types(types)` | Filter by multiple types |
| `by_severity(severity)` | Filter by severity level |
| `in_file(path)` | Filter by file path |
| `in_directory(path)` | Filter by directory |
| `filter(predicate)` | Filter by callable |

### Aggregation

| Method | Returns | Description |
|--------|---------|-------------|
| `group_by_file()` | `dict[Path, list]` | Group by file |
| `group_by_type()` | `dict[str, list]` | Group by type |
| `count_by_type()` | `dict[str, int]` | Count per type |
| `count_by_severity()` | `dict[str, int]` | Count per severity |
| `count_by_file()` | `dict[Path, int]` | Count per file |

### Sorting

| Method | Returns | Description |
|--------|---------|-------------|
| `sorted_by_severity()` | `AnalysisTargetList` | Sort by severity |
| `sorted_by_location()` | `AnalysisTargetList` | Sort by file/line |

### Output

| Method | Returns | Description |
|--------|---------|-------------|
| `summary()` | `str` | Summary string |
| `to_list_of_dicts()` | `list[dict]` | Export as dicts |

## AnalysisConfig

Configuration for analysis.

### Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `max_complexity` | `int` | 10 | Cyclomatic complexity threshold |
| `max_nesting_depth` | `int` | 4 | Maximum nesting levels |
| `max_function_lines` | `int` | 50 | Maximum function length |
| `max_class_lines` | `int` | 300 | Maximum class length |
| `max_parameters` | `int` | 5 | Maximum parameters |
| `max_branches` | `int` | 8 | Maximum if/elif branches |
| `max_returns` | `int` | 4 | Maximum return statements |
| `ignore_files` | `list[str]` | `[]` | Glob patterns to ignore |
| `ignore_functions` | `list[str]` | `[]` | Function names to ignore |
| `ignore_types` | `list[str]` | `[]` | Issue types to ignore |

### Usage

```python
from rejig import Rejig, AnalysisConfig

config = AnalysisConfig(
    max_complexity=15,
    max_function_lines=100,
    ignore_files=["**/test_*.py"],
    ignore_types=["TODO_COMMENT"],
)

rj = Rejig("src/")
issues = rj.find_analysis_issues(config=config)
```

## Analyzers

### ComplexityAnalyzer

Analyze code complexity.

```python
from rejig import Rejig, ComplexityAnalyzer

rj = Rejig("src/")
analyzer = ComplexityAnalyzer(rj)

# Analyze single function
func = rj.find_function("process")
complexity = analyzer.analyze_function(func)
print(f"Cyclomatic: {complexity.cyclomatic}")
print(f"Nesting: {complexity.max_nesting}")

# Find complex functions
complex_funcs = analyzer.find_complex_functions(threshold=10)
for func, c in complex_funcs:
    print(f"{func.name}: {c.cyclomatic}")
```

### DeadCodeAnalyzer

Find unused code.

```python
from rejig import Rejig, DeadCodeAnalyzer

rj = Rejig("src/")
analyzer = DeadCodeAnalyzer(rj)

# Find unused elements
unused_funcs = analyzer.find_unused_functions()
unused_classes = analyzer.find_unused_classes()
unused_imports = analyzer.find_unused_imports()
unused_vars = analyzer.find_unused_variables()
```

### PatternFinder

Find code patterns.

```python
from rejig import Rejig, PatternFinder

rj = Rejig("src/")
finder = PatternFinder(rj)

magic_numbers = finder.find_magic_numbers()
hardcoded_strings = finder.find_hardcoded_strings()
bare_excepts = finder.find_bare_excepts()
todos = finder.find_todos()
```

## AnalysisReporter

Generate reports from findings.

```python
from rejig import Rejig, AnalysisReporter

rj = Rejig("src/")
issues = rj.find_analysis_issues()
reporter = AnalysisReporter(issues)

# Text report
print(reporter.to_text())

# JSON report
json_report = reporter.to_json()

# Markdown report
md_report = reporter.to_markdown()

# HTML report
html_report = reporter.to_html(
    include_code_snippets=True,
    syntax_highlight=True,
)
```
