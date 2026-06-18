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
| `name` | `str \| None` | Name of the element |
| `message` | `str` | Human-readable description |
| `severity` | `str` | "info", "warning", or "error" |
| `value` | `int \| float \| str \| None` | Actual value (e.g., complexity score) |
| `threshold` | `int \| float \| None` | Threshold that was exceeded |
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
| `to_function_target()` | `Target` | Get the function the finding refers to |
| `to_class_target()` | `Target` | Get the class the finding refers to |
| `exists()` | `bool` | Always True for valid findings |

## AnalysisTargetList

List of analysis findings with filtering and aggregation.

### Filtering

| Method | Description |
|--------|-------------|
| `by_type(type)` | Filter by single type |
| `by_types(*types)` | Filter by multiple types |
| `by_severity(severity)` | Filter by severity level |
| `in_file(path)` | Filter by file path |
| `in_directory(path)` | Filter by directory |
| `filter(predicate)` | Filter by callable |
| `errors()` | Findings with `"error"` severity |
| `warnings()` | Findings with `"warning"` severity |
| `info()` | Findings with `"info"` severity |
| `complexity_issues()` | Complexity-related findings only |
| `dead_code()` | Dead-code findings only |
| `pattern_issues()` | Pattern/quality findings only |
| `above_threshold(threshold)` | Findings whose value exceeds `threshold` |
| `below_threshold(threshold)` | Findings whose value is under `threshold` |

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
| `sorted_by_value()` | `AnalysisTargetList` | Sort by finding value (e.g. complexity) |

### Output

| Method | Returns | Description |
|--------|---------|-------------|
| `summary()` | `str` | Summary string |
| `to_list_of_dicts()` | `list[dict]` | Export as dicts |

## Running Analysis

Use `Rejig.analyze_code()` to run a full analysis. It returns an `AnalysisReport`
object aggregating complexity, pattern, dead-code, and coverage findings.

```python
rj.analyze_code(
    include_complexity: bool = True,
    include_patterns: bool = True,
    include_dead_code: bool = True,
    include_coverage: bool = True,
) -> AnalysisReport
```

### Usage

```python
from rejig import Rejig

rj = Rejig("src/")
report = rj.analyze_code()

print(report)                       # Formatted summary
print(f"Total issues: {report.total_issues}")

# Each category is an AnalysisTargetList (or None if disabled)
for finding in report.complexity_issues:
    print(f"{finding.location}: {finding.message}")
```

To skip a category, pass the corresponding flag as `False`:

```python
report = rj.analyze_code(include_coverage=False)
```

### AnalysisReport

| Attribute | Type | Description |
|-----------|------|-------------|
| `generated_at` | `datetime` | When the report was generated |
| `project_root` | `Path` | Analyzed root directory |
| `summary` | `dict` | Project-level metrics |
| `complexity_issues` | `AnalysisTargetList \| None` | Complexity findings |
| `pattern_issues` | `AnalysisTargetList \| None` | Pattern/quality findings |
| `dead_code` | `AnalysisTargetList \| None` | Dead-code findings |
| `coverage_gaps` | `list[Path]` | Files lacking tests |
| `total_issues` | `int` | Total findings across categories (property) |

## Analyzers

For finer control, the individual analyzers can be used directly. Each one is
constructed with a `Rejig` instance and returns `AnalysisTargetList` results.

### ComplexityAnalyzer

Analyze code complexity.

```python
from rejig import Rejig, ComplexityAnalyzer

rj = Rejig("src/")
analyzer = ComplexityAnalyzer(rj)

# Raw per-function complexity results
results = analyzer.analyze_all()
for result in results:
    print(f"{result.full_name}: {result.cyclomatic_complexity}")

# Findings exceeding thresholds
complex_funcs = analyzer.find_complex_functions(max_complexity=10)
long_funcs = analyzer.find_long_functions(max_lines=50)
long_classes = analyzer.find_long_classes(max_lines=500)
deeply_nested = analyzer.find_deeply_nested(max_depth=4)
many_params = analyzer.find_functions_with_many_parameters(max_params=5)
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
no_type_hints = finder.find_functions_without_type_hints()
no_docstrings = finder.find_functions_without_docstrings()
all_patterns = finder.find_all_patterns()
```

## AnalysisReporter

Generate reports from a project. The reporter is constructed with a `Rejig`
instance (it runs the analyzers itself).

```python
from rejig import Rejig, AnalysisReporter

rj = Rejig("src/")
reporter = AnalysisReporter(rj)

# Full AnalysisReport object (same as rj.analyze_code())
report = reporter.generate_full_report()

# Write specific reports to disk (or return data when output_path is None)
reporter.generate_api_summary("reports/api.md")
reporter.generate_module_structure("reports/structure.md")
reporter.generate_complexity_report("reports/complexity.md")
reporter.generate_coverage_gaps_report("reports/coverage.md")
```
