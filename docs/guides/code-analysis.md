# Code Analysis

Rejig provides comprehensive code analysis tools to detect complexity issues, dead code, missing documentation, and code patterns that may indicate problems.

## Quick Start

```python
from rejig import Rejig

rj = Rejig("src/")

# Get all analysis issues
issues = rj.find_analysis_issues()

# Print summary
print(issues.summary())
# Output: Total: 42 issues (3 high, 15 medium, 24 low)

# List all issues
for issue in issues:
    print(f"{issue.severity}: {issue.file_path}:{issue.line_number}")
    print(f"  {issue.type}: {issue.message}")
```

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

### By Type

```python
issues = rj.find_analysis_issues()

# Single type
complexity = issues.by_type("HIGH_CYCLOMATIC_COMPLEXITY")

# Multiple types
docs_issues = issues.by_types([
    "MISSING_TYPE_HINT",
    "MISSING_DOCSTRING"
])

# Dead code issues
dead_code = issues.by_types([
    "UNUSED_FUNCTION",
    "UNUSED_CLASS",
    "UNUSED_VARIABLE",
    "UNUSED_IMPORT"
])
```

### By Severity

```python
# Filter by severity level
high = issues.by_severity("high")
medium = issues.by_severity("medium")
low = issues.by_severity("low")

# Or combine
critical = issues.by_severity(["high", "critical"])
```

### By Location

```python
# Issues in a specific file
file_issues = issues.in_file("src/utils.py")

# Issues in a directory
api_issues = issues.in_directory("src/api/")

# Issues in specific files (by pattern)
test_issues = issues.filter(lambda i: "test" in str(i.file_path))
```

## Grouping and Aggregation

### Group by File

```python
by_file = issues.group_by_file()

for file_path, file_issues in by_file.items():
    print(f"{file_path}:")
    for issue in file_issues:
        print(f"  L{issue.line_number}: {issue.type}")
```

### Group by Type

```python
by_type = issues.group_by_type()

for issue_type, type_issues in by_type.items():
    print(f"{issue_type}: {len(type_issues)} occurrences")
```

### Count Statistics

```python
# Count by type
type_counts = issues.count_by_type()
# {"HIGH_CYCLOMATIC_COMPLEXITY": 5, "MISSING_DOCSTRING": 12, ...}

# Count by severity
severity_counts = issues.count_by_severity()
# {"high": 3, "medium": 15, "low": 24}

# Count by file
file_counts = issues.count_by_file()
# {Path("src/utils.py"): 8, Path("src/api.py"): 3, ...}
```

## Complexity Analysis

### Cyclomatic Complexity

```python
from rejig import ComplexityAnalyzer

analyzer = ComplexityAnalyzer(rj)

# Analyze a specific function
func = rj.find_function("process_data")
complexity = analyzer.analyze_function(func)

print(f"Cyclomatic complexity: {complexity.cyclomatic}")
print(f"Nesting depth: {complexity.max_nesting}")
print(f"Lines of code: {complexity.lines}")
print(f"Branch count: {complexity.branches}")
print(f"Return count: {complexity.returns}")
```

### Find Complex Functions

```python
# Get all functions sorted by complexity
complex_funcs = analyzer.find_complex_functions(threshold=10)

for func, complexity in complex_funcs:
    print(f"{func.name}: complexity={complexity.cyclomatic}")
```

### Nesting Analysis

```python
# Find deeply nested code
deep_nesting = analyzer.find_deep_nesting(max_depth=4)

for location in deep_nesting:
    print(f"{location.file_path}:{location.line_number}")
    print(f"  Nesting depth: {location.depth}")
```

## Dead Code Detection

### Find Unused Functions

```python
from rejig import DeadCodeAnalyzer

analyzer = DeadCodeAnalyzer(rj)

# Find unused functions
unused_funcs = analyzer.find_unused_functions()

for func in unused_funcs:
    print(f"Unused: {func.file_path}:{func.name}")
    print(f"  Defined at line {func.line_number}")
    print(f"  Confidence: {func.confidence}")  # high, medium, low
```

### Find Unused Classes

```python
unused_classes = analyzer.find_unused_classes()

for cls in unused_classes:
    print(f"Unused class: {cls.name}")
```

### Find Unused Variables

```python
unused_vars = analyzer.find_unused_variables()

for var in unused_vars:
    print(f"Unused: {var.name} in {var.file_path}:{var.line_number}")
```

### Find Unused Imports

```python
unused_imports = analyzer.find_unused_imports()

for imp in unused_imports:
    print(f"Unused import: {imp.import_statement}")

# Auto-remove unused imports
for file in rj.find_files():
    file.find_unused_imports().delete_all()
```

### Confidence Levels

Dead code detection has confidence levels:

- **high**: Definitely unused (no references found)
- **medium**: Likely unused (only dynamic references possible)
- **low**: Possibly unused (complex reference patterns)

```python
# Only act on high-confidence findings
high_confidence = unused_funcs.filter(lambda f: f.confidence == "high")
```

## Pattern Detection

### Find Magic Numbers

```python
from rejig import PatternFinder

finder = PatternFinder(rj)

# Find magic numbers (numeric literals that should be constants)
magic_numbers = finder.find_magic_numbers(
    ignore=[0, 1, -1, 2],  # Common acceptable values
    min_occurrences=2,     # Only if used multiple times
)

for match in magic_numbers:
    print(f"Magic number {match.value} at {match.file_path}:{match.line_number}")
```

### Find Hardcoded Strings

```python
# Find strings that might be configuration
hardcoded = finder.find_hardcoded_strings(
    patterns=[
        r"https?://",      # URLs
        r"[a-z]+@[a-z]+",  # Emails
        r"/[a-z/]+",       # Paths
    ]
)

for match in hardcoded:
    print(f"Hardcoded: {match.value!r}")
```

### Find Bare Excepts

```python
bare_excepts = finder.find_bare_excepts()

for match in bare_excepts:
    print(f"Bare except at {match.file_path}:{match.line_number}")
```

### Find TODO Comments

```python
todos = finder.find_todos()

for todo in todos:
    print(f"{todo.todo_type}: {todo.text}")
    print(f"  {todo.file_path}:{todo.line_number}")
```

## Code Metrics

### File Metrics

```python
from rejig import CodeMetrics

metrics = CodeMetrics(rj)

# Get metrics for a file
file_metrics = metrics.analyze_file("src/utils.py")

print(f"Lines of code: {file_metrics.loc}")
print(f"Blank lines: {file_metrics.blank_lines}")
print(f"Comment lines: {file_metrics.comment_lines}")
print(f"Functions: {file_metrics.function_count}")
print(f"Classes: {file_metrics.class_count}")
print(f"Imports: {file_metrics.import_count}")
print(f"Average complexity: {file_metrics.avg_complexity}")
```

### Project Metrics

```python
# Get aggregated metrics
project_metrics = metrics.analyze_project()

print(f"Total files: {project_metrics.file_count}")
print(f"Total LOC: {project_metrics.total_loc}")
print(f"Total functions: {project_metrics.total_functions}")
print(f"Total classes: {project_metrics.total_classes}")
print(f"Avg file size: {project_metrics.avg_file_size}")
print(f"Largest file: {project_metrics.largest_file}")
```

## Working with Findings

### Navigate to Code

```python
issues = rj.find_analysis_issues()

for issue in issues:
    # Get the file target
    file_target = issue.to_file_target()

    # Get the line target
    line_target = issue.to_line_target()

    # Fix the issue directly
    if issue.type == "BARE_EXCEPT":
        line_target.rewrite("except Exception:")
```

### Auto-Fix Issues

```python
# Fix missing docstrings
missing_docs = issues.by_type("MISSING_DOCSTRING")
for issue in missing_docs:
    target = rj.find_function(issue.name) or rj.find_class(issue.name)
    if target:
        target.generate_docstring()

# Fix missing type hints
missing_types = issues.by_type("MISSING_TYPE_HINT")
for issue in missing_types:
    func = rj.find_function(issue.name)
    if func:
        func.infer_type_hints()

# Remove unused imports
unused = issues.by_type("UNUSED_IMPORT")
for issue in unused:
    rj.file(issue.file_path).remove_import(issue.name)
```

## Generating Reports

### Text Report

```python
from rejig import AnalysisReporter

reporter = AnalysisReporter(issues)

# Simple text report
print(reporter.to_text())

# Detailed report
print(reporter.to_text(verbose=True))
```

### JSON Report

```python
# JSON for CI integration
json_report = reporter.to_json()
print(json_report)

# Save to file
with open("analysis-report.json", "w") as f:
    f.write(json_report)
```

### Markdown Report

```python
# Markdown for documentation
md_report = reporter.to_markdown()

with open("analysis-report.md", "w") as f:
    f.write(md_report)
```

### HTML Report

```python
# HTML with syntax highlighting
html_report = reporter.to_html(
    include_code_snippets=True,
    syntax_highlight=True,
)

with open("analysis-report.html", "w") as f:
    f.write(html_report)
```

## CI Integration

### Exit Codes

```python
#!/usr/bin/env python
"""CI script for code analysis."""
import sys
from rejig import Rejig

rj = Rejig("src/")
issues = rj.find_analysis_issues()

# Fail on high severity issues
high_severity = issues.by_severity("high")
if high_severity:
    print(f"Found {len(high_severity)} high severity issues:")
    for issue in high_severity:
        print(f"  {issue.file_path}:{issue.line_number}: {issue.message}")
    sys.exit(1)

# Warn on medium severity
medium_severity = issues.by_severity("medium")
if medium_severity:
    print(f"Warning: {len(medium_severity)} medium severity issues")
    for issue in medium_severity:
        print(f"  {issue.file_path}:{issue.line_number}: {issue.message}")

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
          path: analysis-report.html
```

## Thresholds and Configuration

### Custom Thresholds

```python
from rejig import Rejig, AnalysisConfig

config = AnalysisConfig(
    max_complexity=15,          # Default: 10
    max_nesting_depth=5,        # Default: 4
    max_function_lines=100,     # Default: 50
    max_class_lines=500,        # Default: 300
    max_parameters=8,           # Default: 5
    max_branches=10,            # Default: 8
    max_returns=5,              # Default: 4
)

rj = Rejig("src/")
issues = rj.find_analysis_issues(config=config)
```

### Ignore Patterns

```python
config = AnalysisConfig(
    ignore_files=["**/test_*.py", "**/migrations/*.py"],
    ignore_functions=["__init__", "__repr__"],
    ignore_types=["TODO_COMMENT"],  # Don't report TODOs
)
```
