# Code Analysis

Rejig provides comprehensive code analysis tools to detect complexity issues, dead code, missing documentation, and code patterns that may indicate problems.

## Quick Start

```python
from rejig import Rejig

rj = Rejig("src/")

# Generate a comprehensive analysis report
report = rj.analyze_code()

# Print the human-readable report
print(report)
print(f"Total issues: {report.total_issues}")

# The report groups findings into AnalysisTargetLists
for finding in report.complexity_issues:
    print(f"{finding.severity}: {finding.location}")
    print(f"  {finding.type.name}: {finding.message}")
```

`analyze_code()` returns an `AnalysisReport` with `complexity_issues`,
`pattern_issues`, `dead_code`, and `coverage_gaps`. Each issue group is an
`AnalysisTargetList`. You can also call the individual finders directly (see
below) when you only need one category.

## Analysis Types

Rejig detects the following types of issues:

### Complexity Issues

| Type | Description |
|------|-------------|
| `HIGH_CYCLOMATIC_COMPLEXITY` | Function has too many branches |
| `DEEP_NESTING` | Code nested too deeply |
| `LONG_FUNCTION` | Function has too many lines |
| `LONG_CLASS` | Class has too many lines/methods |
| `TOO_MANY_PARAMETERS` | Function has too many parameters |
| `TOO_MANY_BRANCHES` | Too many if/elif branches |
| `TOO_MANY_RETURNS` | Function has too many return statements |

### Documentation Issues

| Type | Description |
|------|-------------|
| `MISSING_TYPE_HINT` | Function lacks type annotations |
| `MISSING_DOCSTRING` | Public function/class lacks docstring |

### Code Quality Issues

| Type | Description |
|------|-------------|
| `BARE_EXCEPT` | Catching all exceptions without specificity |
| `HARDCODED_STRING` | Magic string that should be a constant |
| `MAGIC_NUMBER` | Numeric literal that should be named |
| `TODO_COMMENT` | TODO/FIXME comment in code |

### Dead Code Issues

| Type | Description |
|------|-------------|
| `UNUSED_FUNCTION` | Function is never called |
| `UNUSED_CLASS` | Class is never instantiated or subclassed |
| `UNUSED_VARIABLE` | Variable is assigned but never used |
| `UNUSED_IMPORT` | Import is never used |
| `UNREACHABLE_CODE` | Code after return/raise/break |

## Filtering Issues

Every finder (and every `AnalysisReport` group) returns an `AnalysisTargetList`
that supports filtering. Finding types are members of the `AnalysisType` enum,
and severities are the strings `"info"`, `"warning"`, and `"error"`.

### By Type

```python
from rejig import AnalysisType

issues = rj.find_complex_functions()

# Single type
complexity = issues.by_type(AnalysisType.HIGH_CYCLOMATIC_COMPLEXITY)

# Multiple types (variadic)
docs_issues = report.pattern_issues.by_types(
    AnalysisType.MISSING_TYPE_HINT,
    AnalysisType.MISSING_DOCSTRING,
)

# Category shortcuts
dead_code = report.dead_code.dead_code()
patterns = report.pattern_issues.pattern_issues()
complexity = report.complexity_issues.complexity_issues()
```

### By Severity

```python
# Filter by severity level ("info", "warning", "error")
errors = issues.by_severity("error")
warnings = issues.by_severity("warning")
info = issues.by_severity("info")

# Severity shortcuts
errors = issues.errors()
warnings = issues.warnings()
info = issues.info()
```

### By Location

```python
# Issues in a specific file
file_issues = issues.in_file("src/utils.py")

# Issues in a directory
api_issues = issues.in_directory("src/api/")

# Issues matching a custom predicate
test_issues = issues.filter(lambda i: "test" in str(i.file_path))
```

### By Value

```python
# Findings carry a numeric value (complexity score, line count, etc.)
very_complex = rj.find_complex_functions().above_threshold(20)
sorted_issues = rj.find_complex_functions().sorted_by_value(descending=True)
```

## Grouping and Aggregation

### Group by File

```python
issues = rj.find_complex_functions()
by_file = issues.group_by_file()

for file_path, file_issues in by_file.items():
    print(f"{file_path}:")
    for issue in file_issues:
        print(f"  L{issue.line_number}: {issue.type.name}")
```

### Group by Type

```python
by_type = issues.group_by_type()

for issue_type, type_issues in by_type.items():
    print(f"{issue_type.name}: {len(type_issues)} occurrences")
```

### Count Statistics

```python
# Count by type (keys are AnalysisType enum members)
type_counts = issues.count_by_type()
# {AnalysisType.HIGH_CYCLOMATIC_COMPLEXITY: 5, ...}

# Count by severity (keys are "info" / "warning" / "error")
severity_counts = issues.count_by_severity()
# {"warning": 3, "info": 15}

# Count by file
file_counts = issues.count_by_file()
# {Path("src/utils.py"): 8, Path("src/api.py"): 3, ...}

# A one-line summary string
print(issues.summary())
```

## Complexity Analysis

### Cyclomatic Complexity

```python
from rejig import ComplexityAnalyzer

analyzer = ComplexityAnalyzer(rj)

# Analyze every function/method in the working set
results = analyzer.analyze_all()

for result in results:
    print(f"{result.full_name}: {result.file_path}:{result.line_number}")
    print(f"  Cyclomatic complexity: {result.cyclomatic_complexity}")
    print(f"  Lines: {result.line_count}")
    print(f"  Parameters: {result.parameter_count}")
    print(f"  Branches: {result.branch_count}")
    print(f"  Returns: {result.return_count}")
```

### Find Complex Functions

```python
# Returns an AnalysisTargetList of findings above the threshold
complex_funcs = analyzer.find_complex_functions(max_complexity=10)

for finding in complex_funcs:
    print(f"{finding.name}: complexity={finding.value}")

# Also available directly on Rejig
complex_funcs = rj.find_complex_functions(max_complexity=15)
```

### Nesting Analysis

```python
# Find deeply nested code (returns an AnalysisTargetList)
deep_nesting = analyzer.find_deeply_nested(max_depth=4)

for finding in deep_nesting:
    print(f"{finding.file_path}:{finding.line_number}")
    print(f"  Nesting depth: {finding.value}")

# Also available directly on Rejig
deep_nesting = rj.find_deeply_nested(max_depth=4)
```

## Dead Code Detection

Dead code detection is heuristic and may produce false positives (for example,
callbacks, decorators, dynamically referenced names, or entry points). Review
findings before acting on them.

### Find Unused Functions

```python
from rejig import DeadCodeAnalyzer

analyzer = DeadCodeAnalyzer(rj)

# Find unused functions (returns an AnalysisTargetList)
unused_funcs = analyzer.find_unused_functions()

for finding in unused_funcs:
    print(f"Unused: {finding.name} in {finding.file_path}")
    print(f"  Defined at line {finding.line_number}")

# Also available directly on Rejig
unused_funcs = rj.find_unused_functions()
```

### Find Unused Classes

```python
unused_classes = analyzer.find_unused_classes()

for finding in unused_classes:
    print(f"Unused class: {finding.name}")
```

### Find Unused Variables

```python
unused_vars = analyzer.find_unused_variables()

for finding in unused_vars:
    print(f"Unused: {finding.name} in {finding.location}")
```

### Find Unreachable Code

```python
unreachable = analyzer.find_unreachable_code()

for finding in unreachable:
    print(f"Unreachable: {finding.location}")
```

### Find Unused Imports

Unused imports are handled by the import tooling, not the dead-code analyzer:

```python
# Across the project
unused_imports = rj.find_unused_imports()

for imp in unused_imports:
    print(f"Unused import at {imp.file_path}:{imp.line_number}")

# Per file: find and remove
for file in rj.find_files():
    file.remove_unused_imports()
```

## Pattern Detection

### Find Magic Numbers

```python
from rejig import PatternFinder

finder = PatternFinder(rj)

# Find magic numbers (numeric literals that should be constants).
# A built-in allow-list excludes common values (0, 1, 2, 10, 100, ...).
magic_numbers = finder.find_magic_numbers()

for finding in magic_numbers:
    print(f"Magic number {finding.value} at {finding.location}")

# Also available directly on Rejig
magic_numbers = rj.find_magic_numbers()
```

### Find Hardcoded Strings

```python
# Find string literals at least `min_length` characters long
hardcoded = finder.find_hardcoded_strings(min_length=10)

for finding in hardcoded:
    print(f"Hardcoded: {finding.value!r} at {finding.location}")

# Also available directly on Rejig
hardcoded = rj.find_hardcoded_strings(min_length=20)
```

### Find Bare Excepts

```python
bare_excepts = finder.find_bare_excepts()

for finding in bare_excepts:
    print(f"Bare except at {finding.location}")
```

### Find TODO Comments

TODO comments are found project-wide via `Rejig.find_todos()`:

```python
todos = rj.find_todos()

for todo in todos:
    print(f"{todo.todo_type}: {todo.todo_text}")
    print(f"  {todo.location}")
```

## Code Metrics

### File Metrics

```python
from pathlib import Path
from rejig import CodeMetrics

metrics = CodeMetrics(rj)

# Get metrics for a file (a FileMetrics dataclass)
file_metrics = metrics.get_file_metrics(Path("src/utils.py"))

print(f"Total lines: {file_metrics.total_lines}")
print(f"Code lines: {file_metrics.code_lines}")
print(f"Blank lines: {file_metrics.blank_lines}")
print(f"Comment lines: {file_metrics.comment_lines}")
print(f"Functions: {file_metrics.function_count}")
print(f"Classes: {file_metrics.class_count}")
print(f"Imports: {file_metrics.import_count}")
print(f"Average complexity: {file_metrics.avg_complexity}")
```

### Project Metrics

```python
# Get an aggregated summary dict for the whole project
summary = metrics.get_project_summary()

print(f"Total files: {summary['total_files']}")
print(f"Total lines: {summary['total_lines']}")
print(f"Total functions: {summary['total_functions']}")
print(f"Total classes: {summary['total_classes']}")
print(f"Avg file size: {summary.get('avg_file_size')}")

# Shortcut on Rejig
summary = rj.get_code_metrics_summary()
```

## Working with Findings

### Navigate to Code

```python
from rejig import AnalysisType

issues = rj.find_bare_excepts()

for issue in issues:
    # Get the file target
    file_target = issue.to_file_target()

    # Get the line target
    line_target = issue.to_line_target()

    # Fix the issue directly
    if issue.type == AnalysisType.BARE_EXCEPT:
        line_target.rewrite("    except Exception:")
```

### Auto-Fix Issues

```python
# Generate docstrings for classes that are missing them
for issue in rj.find_classes_without_docstrings():
    cls = rj.find_class(issue.name)
    if cls.exists():
        cls.generate_docstrings()

# Remove unused imports across the project
rj.remove_all_unused_imports()
```

## Generating Reports

### Full Report

```python
from rejig import AnalysisReporter

reporter = AnalysisReporter(rj)

# Build a comprehensive AnalysisReport
report = reporter.generate_full_report()

# AnalysisReport renders to a human-readable string
print(report)
print(f"Total issues: {report.total_issues}")

# Equivalent shortcut on Rejig
report = rj.analyze_code()
```

### Complexity Report (JSON)

```python
# Returns a Result; pass an output path to write to disk
result = reporter.generate_complexity_report("reports/complexity.json")
print(result.message)

# Without a path, the JSON data is returned in result.data
result = reporter.generate_complexity_report()
data = result.data
```

### API Summary and Module Structure

```python
# Markdown API summary
reporter.generate_api_summary("docs/api.md")

# Module structure tree
reporter.generate_module_structure("docs/structure.md")

# Files lacking test coverage
reporter.generate_coverage_gaps_report("reports/coverage-gaps.md")
```

## CI Integration

### Exit Codes

```python
#!/usr/bin/env python
"""CI script for code analysis."""
import sys
from rejig import Rejig

rj = Rejig("src/")
report = rj.analyze_code()

# Combine all finding groups
all_issues = (
    list(report.complexity_issues or [])
    + list(report.pattern_issues or [])
    + list(report.dead_code or [])
)

# Fail on error-severity findings
errors = [i for i in all_issues if i.severity == "error"]
if errors:
    print(f"Found {len(errors)} error-severity issues:")
    for issue in errors:
        print(f"  {issue.location}: {issue.message}")
    sys.exit(1)

# Warn on warning-severity findings
warnings = [i for i in all_issues if i.severity == "warning"]
if warnings:
    print(f"Warning: {len(warnings)} warning-severity issues")
    for issue in warnings:
        print(f"  {issue.location}: {issue.message}")

print("Analysis passed!")
sys.exit(0)
```

### GitHub Actions Integration

```yaml
# .github/workflows/analysis.yml
name: Code Analysis

on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install rejig

      - name: Run analysis
        run: python scripts/analyze.py

      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: analysis-report
          path: reports/complexity.json
```

## Thresholds

Thresholds are passed as arguments to the individual finders. Each finder
applies its own default when no value is given:

```python
rj = Rejig("src/")

rj.find_complex_functions(max_complexity=15)              # default: 10
rj.find_deeply_nested(max_depth=5)                        # default: 4
rj.find_long_functions(max_lines=100)                     # default: 50
rj.find_long_classes(max_lines=500)                       # default: 500
rj.find_functions_with_many_parameters(max_params=8)      # default: 5
rj.find_hardcoded_strings(min_length=20)                  # default: 10
```

The combined `ComplexityAnalyzer` also accepts thresholds at once:

```python
from rejig import ComplexityAnalyzer

analyzer = ComplexityAnalyzer(rj)
issues = analyzer.find_all_complexity_issues(
    max_complexity=15,
    max_lines=100,
    max_class_lines=500,
    max_depth=5,
    max_params=8,
)
```

Filter results to a specific scope using the `AnalysisTargetList` methods shown
earlier (`in_file`, `in_directory`, `filter`):

```python
issues = rj.find_complex_functions().filter(
    lambda i: "test" not in str(i.file_path)
)
```
