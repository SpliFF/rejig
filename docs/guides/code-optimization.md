# Code Optimization

Analyze and improve code efficiency with the optimize module.

## Overview

The `optimize` module provides two analyzers:

- **DRYAnalyzer** — Find duplicate code, expressions, and literals
- **LoopOptimizer** — Find loops that can be replaced with comprehensions or builtins

Both return `OptimizeTargetList` objects for filtering and inspection.

## DRY Analysis

### Finding Duplicate Code

```python
from rejig import Rejig, DRYAnalyzer

rj = Rejig("src/")
dry = DRYAnalyzer(rj)

# Find all DRY violations
issues = dry.find_all_issues()
print(issues.summary())
```

Output:
```
Total: 15 optimization opportunities
  DUPLICATE_CODE_BLOCK: 4
  DUPLICATE_LITERAL: 6
  SIMILAR_FUNCTION: 3
  DUPLICATE_EXPRESSION: 2
```

### Duplicate Code Blocks

Find repeated code in if/for/while/try/with blocks:

```python
# Find blocks repeated 2+ times with 3+ lines
duplicates = dry.find_duplicate_code_blocks(
    min_lines=3,
    min_occurrences=2
)

for dup in duplicates:
    print(f"{dup.location}: {dup.message}")
    print(f"  Other locations: {dup.finding.context['other_locations']}")
```

### Duplicate Expressions

Find repeated complex expressions:

```python
expressions = dry.find_duplicate_expressions(min_occurrences=3)

for expr in expressions:
    print(f"{expr.location}: {expr.original_code}")
    print(f"  Suggestion: {expr.suggested_code}")
```

### Magic Numbers and Strings

Find repeated literals that should be constants:

```python
literals = dry.find_duplicate_literals(min_occurrences=3)

for lit in literals:
    print(f"{lit.location}: {lit.original_code}")
    # Output: src/config.py:45: 3600
    # Suggestion: Define a constant: TIMEOUT_SECONDS = 3600
```

### Similar Functions

Find functions with identical structure:

```python
similar = dry.find_similar_functions()

for func in similar:
    print(f"{func.name}: identical to {func.finding.context['similar_functions']}")
```

## Loop Optimization

### Finding Loop Issues

```python
from rejig import Rejig, LoopOptimizer

rj = Rejig("src/")
loops = LoopOptimizer(rj)

# Find all loop optimization opportunities
issues = loops.find_all_issues()
print(issues.summary())
```

### List Comprehension Candidates

```python
comprehensions = loops.find_comprehension_opportunities()

for opt in comprehensions:
    print(f"{opt.location}:")
    print(f"  Before: {opt.original_code}")
    print(f"  After:  {opt.suggested_code}")
```

Example findings:

```
src/utils.py:23:
  Before: for item in items:
              result.append(item.upper())
  After:  result = [item.upper() for item in items]

src/data.py:45:
  Before: for key, value in pairs:
              data[key] = value * 2
  After:  data = {key: value * 2 for key, value in pairs}
```

### Builtin Function Candidates

```python
builtins = loops.find_builtin_opportunities()

for opt in builtins:
    print(f"{opt.location}: {opt.message}")
    print(f"  Suggested: {opt.suggested_code}")
```

Detects patterns for:

| Pattern | Builtin |
|---------|---------|
| Loop summing values | `sum()` |
| Loop with conditional return True | `any()` |
| Loop with conditional return False | `all()` |
| Loop building string | `str.join()` |
| Loop applying function | `map()` |
| Loop filtering items | `filter()` or comprehension |

### Iterator Improvements

```python
iterators = loops.find_iterator_opportunities()

for opt in iterators:
    print(f"{opt.location}: {opt.message}")
```

Detects:

- Manual index tracking → `enumerate()`
- `range(len(x))` patterns → direct iteration or `zip()`

## Filtering Results

### By Type

```python
# Only DRY issues
issues.dry_issues()

# Only loop issues
issues.loop_issues()

# Specific type
from rejig import OptimizeType
issues.by_type(OptimizeType.SLOW_LOOP_TO_COMPREHENSION)
```

### By Location

```python
# In a specific file
issues.in_file("src/models.py")

# In a directory
issues.in_directory("src/utils/")
```

### By Severity

```python
issues.warnings()    # Higher confidence findings
issues.suggestions() # Lower confidence findings
issues.info()        # Informational
```

## Grouping and Aggregation

### Group by File

```python
by_file = issues.group_by_file()
for path, file_issues in by_file.items():
    print(f"{path}: {len(file_issues)} issues")
```

### Group by Type

```python
by_type = issues.group_by_type()
for opt_type, type_issues in by_type.items():
    print(f"{opt_type.name}: {len(type_issues)}")
```

### Counts

```python
issues.count_by_type()      # {OptimizeType: int}
issues.count_by_file()      # {Path: int}
issues.count_by_severity()  # {str: int}
```

## Working with Findings

### Accessing Details

```python
for opt in issues:
    print(f"Type: {opt.type.name}")
    print(f"Location: {opt.location}")
    print(f"Message: {opt.message}")
    print(f"Original: {opt.original_code}")
    print(f"Suggested: {opt.suggested_code}")
    print(f"Improvement: {opt.finding.estimated_improvement}")
    print(f"Context: {opt.finding.context}")
    print()
```

### Navigation

```python
# Navigate to the file
file_target = opt.to_file_target()

# Navigate to the specific line
line_target = opt.to_line_target()

# Navigate to the line range
block_target = opt.to_line_block_target()
```

### Export

```python
# To list of dicts (for JSON export)
data = issues.to_list_of_dicts()

import json
print(json.dumps(data, indent=2, default=str))
```

## Confidence Levels

Loop optimizations include a confidence score:

```python
# Only high-confidence suggestions (>= 0.85)
high_confidence = loops.find_all_issues(min_confidence=0.85)

# Include lower-confidence suggestions
all_suggestions = loops.find_all_issues(min_confidence=0.5)
```

Confidence levels:

| Confidence | Meaning |
|------------|---------|
| 0.95 | Very clear pattern (e.g., simple list append) |
| 0.85-0.94 | Clear pattern with minor ambiguity |
| 0.70-0.84 | Likely correct but context-dependent |
| < 0.70 | Suggestion only, manual review needed |

## Optimization Types

### DRY Types

```python
from rejig import OptimizeType

# Duplicate code
OptimizeType.DUPLICATE_CODE_BLOCK
OptimizeType.DUPLICATE_EXPRESSION
OptimizeType.DUPLICATE_LITERAL
OptimizeType.SIMILAR_FUNCTION
OptimizeType.REPEATED_PATTERN
```

### Loop Types

```python
# Comprehensions
OptimizeType.SLOW_LOOP_TO_COMPREHENSION
OptimizeType.SLOW_LOOP_TO_DICT_COMPREHENSION
OptimizeType.SLOW_LOOP_TO_SET_COMPREHENSION

# Builtins
OptimizeType.SLOW_LOOP_TO_MAP
OptimizeType.SLOW_LOOP_TO_FILTER
OptimizeType.SLOW_LOOP_TO_ANY_ALL
OptimizeType.SLOW_LOOP_TO_SUM
OptimizeType.SLOW_LOOP_TO_JOIN
OptimizeType.SLOW_LOOP_TO_ENUMERATE
OptimizeType.SLOW_LOOP_TO_ZIP
```

### Efficiency Types

```python
OptimizeType.INEFFICIENT_STRING_CONCAT
OptimizeType.INEFFICIENT_LIST_EXTEND
OptimizeType.UNNECESSARY_LIST_CONVERSION
```

## Common Patterns

### Generate Optimization Report

```python
from rejig import Rejig, DRYAnalyzer, LoopOptimizer

def generate_report(path: str) -> str:
    rj = Rejig(path)

    dry = DRYAnalyzer(rj)
    loops = LoopOptimizer(rj)

    dry_issues = dry.find_all_issues()
    loop_issues = loops.find_all_issues()

    lines = ["# Code Optimization Report", ""]

    lines.append("## DRY Violations")
    lines.append(dry_issues.summary())
    lines.append("")

    lines.append("## Loop Optimizations")
    lines.append(loop_issues.summary())
    lines.append("")

    lines.append("## Details")
    for opt in dry_issues.sorted_by_location():
        lines.append(f"- {opt.location}: {opt.message}")

    for opt in loop_issues.sorted_by_location():
        lines.append(f"- {opt.location}: {opt.message}")

    return "\n".join(lines)

print(generate_report("src/"))
```

### Focus on High-Impact Issues

```python
# Find the most frequently duplicated code
dry = DRYAnalyzer(rj)
duplicates = dry.find_duplicate_code_blocks(min_occurrences=3)

# Sort by number of occurrences
sorted_dups = sorted(
    duplicates,
    key=lambda d: d.finding.context.get("occurrences", 0),
    reverse=True
)

print("Top duplicated code blocks:")
for dup in sorted_dups[:5]:
    count = dup.finding.context.get("occurrences", 0)
    print(f"  {count}x: {dup.location}")
```

### CI Integration

```python
#!/usr/bin/env python3
"""Check for optimization opportunities in CI."""

import sys
from rejig import Rejig, DRYAnalyzer, LoopOptimizer

rj = Rejig("src/")

dry = DRYAnalyzer(rj)
loops = LoopOptimizer(rj)

# Only flag high-confidence issues
dry_issues = dry.find_duplicate_code_blocks(min_occurrences=3)
loop_issues = loops.find_all_issues(min_confidence=0.9)

total = len(dry_issues) + len(loop_issues)

if total > 0:
    print(f"Found {total} optimization opportunities:")
    print(dry_issues.summary())
    print(loop_issues.summary())
    sys.exit(1)

print("No major optimization issues found")
sys.exit(0)
```

## Next Steps

- [Optimization Recipes](../examples/optimization-recipes.md) — Ready-to-use scripts
- [Batch Operations](batch-operations.md) — Apply changes to multiple targets
- [Codemod Recipes](../examples/codemod-recipes.md) — More code transformation examples
