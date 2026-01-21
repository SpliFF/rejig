# Optimization Recipes

Ready-to-use scripts for code optimization analysis and reporting.

## Quick Audit

### Full Codebase Scan

```python
from rejig import Rejig, DRYAnalyzer, LoopOptimizer

def audit_codebase(path: str):
    """Run a complete optimization audit."""
    rj = Rejig(path)

    print(f"Auditing: {path}")
    print("=" * 50)

    # DRY Analysis
    dry = DRYAnalyzer(rj)
    dry_issues = dry.find_all_issues()

    print("\nDRY Violations:")
    print(dry_issues.summary())

    # Loop Analysis
    loops = LoopOptimizer(rj)
    loop_issues = loops.find_all_issues()

    print("\nLoop Optimizations:")
    print(loop_issues.summary())

    # Summary
    total = len(dry_issues) + len(loop_issues)
    print(f"\nTotal: {total} optimization opportunities")

    return dry_issues, loop_issues


audit_codebase("src/")
```

### Single File Analysis

```python
def analyze_file(rj: Rejig, file_path: str):
    """Analyze a single file for optimization opportunities."""
    from pathlib import Path

    dry = DRYAnalyzer(rj)
    loops = LoopOptimizer(rj)

    path = Path(file_path)

    dry_issues = dry.find_all_issues().in_file(path)
    loop_issues = loops.find_all_issues().in_file(path)

    print(f"Analysis for {file_path}:")

    if dry_issues:
        print("\nDRY Issues:")
        for issue in dry_issues:
            print(f"  Line {issue.line_number}: {issue.message}")

    if loop_issues:
        print("\nLoop Issues:")
        for issue in loop_issues:
            print(f"  Line {issue.line_number}: {issue.message}")
            print(f"    Suggested: {issue.suggested_code}")

    if not dry_issues and not loop_issues:
        print("  No optimization opportunities found")


rj = Rejig("src/")
analyze_file(rj, "src/utils.py")
```

## DRY Recipes

### Extract Duplicate Code Report

```python
from rejig import Rejig, DRYAnalyzer
from collections import defaultdict

def find_extraction_candidates(rj: Rejig):
    """Find code blocks that should be extracted to functions."""
    dry = DRYAnalyzer(rj)

    duplicates = dry.find_duplicate_code_blocks(
        min_lines=5,       # At least 5 lines
        min_occurrences=2  # At least 2 occurrences
    )

    # Group by hash to find related duplicates
    groups = defaultdict(list)
    for dup in duplicates:
        # Use the original code as a rough grouping key
        key = dup.original_code[:100]
        groups[key].append(dup)

    print("Extraction Candidates:")
    print("=" * 50)

    for i, (_, group) in enumerate(groups.items(), 1):
        print(f"\nCandidate {i}: {len(group)} occurrences")
        print(f"Lines: {group[0].finding.context.get('line_count', '?')}")
        print("Locations:")
        for dup in group:
            print(f"  - {dup.location}")
        print("Sample code:")
        print("  " + group[0].original_code[:200].replace("\n", "\n  "))


rj = Rejig("src/")
find_extraction_candidates(rj)
```

### Magic Number Cleanup

```python
def identify_magic_numbers(rj: Rejig):
    """Find magic numbers and suggest constant names."""
    dry = DRYAnalyzer(rj)

    literals = dry.find_duplicate_literals(min_occurrences=2)

    # Filter to just numbers
    numbers = [
        lit for lit in literals
        if lit.finding.context.get("literal_type") == "integer"
    ]

    print("Magic Numbers Found:")
    print("=" * 50)

    # Group by value
    by_value = {}
    for num in numbers:
        value = num.original_code
        if value not in by_value:
            by_value[value] = []
        by_value[value].append(num)

    # Sort by frequency
    sorted_values = sorted(
        by_value.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    for value, occurrences in sorted_values:
        count = len(occurrences)
        print(f"\n{value} (used {count} times)")

        # Suggest a constant name based on context
        contexts = [o.finding.name for o in occurrences if o.finding.name]
        if contexts:
            suggested_name = suggest_constant_name(value, contexts)
            print(f"  Suggested: {suggested_name} = {value}")

        print("  Locations:")
        for occ in occurrences[:5]:
            print(f"    - {occ.location}")
        if count > 5:
            print(f"    ... and {count - 5} more")


def suggest_constant_name(value: str, contexts: list[str]) -> str:
    """Suggest a constant name based on usage context."""
    # Simple heuristic - in practice, use more sophisticated analysis
    common_patterns = {
        "60": "SECONDS_PER_MINUTE",
        "3600": "SECONDS_PER_HOUR",
        "86400": "SECONDS_PER_DAY",
        "1000": "MILLISECONDS_PER_SECOND",
        "1024": "BYTES_PER_KB",
        "100": "PERCENTAGE_MAX",
    }
    return common_patterns.get(value, f"CONSTANT_{value}")


rj = Rejig("src/")
identify_magic_numbers(rj)
```

### String Constant Extraction

```python
def find_repeated_strings(rj: Rejig, min_length: int = 10):
    """Find repeated string literals that should be constants."""
    dry = DRYAnalyzer(rj)

    literals = dry.find_duplicate_literals(min_occurrences=2)

    # Filter to strings of sufficient length
    strings = [
        lit for lit in literals
        if lit.finding.context.get("literal_type") == "string"
        and len(lit.original_code) >= min_length
    ]

    print(f"Repeated Strings (>= {min_length} chars):")
    print("=" * 50)

    # Group by value
    by_value = {}
    for s in strings:
        value = s.original_code
        if value not in by_value:
            by_value[value] = []
        by_value[value].append(s)

    for value, occurrences in sorted(by_value.items(), key=lambda x: -len(x[1])):
        count = len(occurrences)
        print(f"\n{value[:50]}{'...' if len(value) > 50 else ''}")
        print(f"  Used {count} times")
        print("  Locations:")
        for occ in occurrences[:3]:
            print(f"    - {occ.location}")


rj = Rejig("src/")
find_repeated_strings(rj)
```

### Similar Function Consolidation

```python
def find_consolidation_candidates(rj: Rejig):
    """Find similar functions that could be merged."""
    dry = DRYAnalyzer(rj)

    similar = dry.find_similar_functions()

    if not similar:
        print("No similar functions found")
        return

    print("Similar Function Groups:")
    print("=" * 50)

    # Group by similarity
    seen = set()
    groups = []

    for func in similar:
        if func.name in seen:
            continue

        similar_names = func.finding.context.get("similar_functions", [])
        group = [func.name] + similar_names

        for name in group:
            seen.add(name)

        groups.append({
            "functions": group,
            "location": func.location,
            "params": func.finding.context.get("param_count"),
            "statements": func.finding.context.get("statement_count"),
        })

    for i, group in enumerate(groups, 1):
        print(f"\nGroup {i}:")
        print(f"  Functions: {', '.join(group['functions'])}")
        print(f"  Parameters: {group['params']}")
        print(f"  Statements: {group['statements']}")
        print("  Suggestion: Consider merging into a single parameterized function")


rj = Rejig("src/")
find_consolidation_candidates(rj)
```

## Loop Recipes

### Comprehension Conversion Guide

```python
def generate_comprehension_fixes(rj: Rejig):
    """Generate copy-paste ready comprehension conversions."""
    loops = LoopOptimizer(rj)

    comprehensions = loops.find_comprehension_opportunities()

    if not comprehensions:
        print("No loop-to-comprehension conversions found")
        return

    print("Loop to Comprehension Conversions:")
    print("=" * 50)

    for opt in comprehensions.sorted_by_location():
        print(f"\n{opt.location}")
        print("-" * 40)
        print("Before:")
        print(indent(opt.original_code, "  "))
        print("\nAfter:")
        print(indent(opt.suggested_code, "  "))
        print(f"\nBenefit: {opt.finding.estimated_improvement}")


def indent(text: str, prefix: str) -> str:
    """Indent each line of text."""
    return "\n".join(prefix + line for line in text.split("\n"))


rj = Rejig("src/")
generate_comprehension_fixes(rj)
```

### Builtin Replacement Guide

```python
def generate_builtin_fixes(rj: Rejig):
    """Generate builtin function replacements."""
    loops = LoopOptimizer(rj)

    builtins = loops.find_builtin_opportunities()

    # Group by builtin type
    by_type = builtins.group_by_type()

    print("Builtin Function Replacements:")
    print("=" * 50)

    for opt_type, issues in by_type.items():
        print(f"\n## {opt_type.name}")
        print(f"Found: {len(issues)} occurrences\n")

        for opt in issues:
            print(f"  {opt.location}")
            print(f"    {opt.suggested_code}")


rj = Rejig("src/")
generate_builtin_fixes(rj)
```

### Performance Hotspot Finder

```python
def find_performance_hotspots(rj: Rejig):
    """Find the most impactful performance improvements."""
    loops = LoopOptimizer(rj)

    all_issues = loops.find_all_issues(min_confidence=0.8)

    # Prioritize by type (some optimizations have bigger impact)
    high_impact_types = {
        "SLOW_LOOP_TO_JOIN",       # O(n) vs O(n²)
        "SLOW_LOOP_TO_SUM",        # C implementation
        "SLOW_LOOP_TO_ANY_ALL",    # Short-circuit
    }

    hotspots = [
        opt for opt in all_issues
        if opt.type.name in high_impact_types
    ]

    print("Performance Hotspots:")
    print("=" * 50)

    if not hotspots:
        print("No high-impact optimizations found")
        return

    for opt in hotspots:
        print(f"\n{opt.location}")
        print(f"  Type: {opt.type.name}")
        print(f"  Impact: {opt.finding.estimated_improvement}")
        print(f"  Fix: {opt.suggested_code}")


rj = Rejig("src/")
find_performance_hotspots(rj)
```

## Report Generation

### Markdown Report

```python
def generate_markdown_report(rj: Rejig) -> str:
    """Generate a comprehensive markdown report."""
    dry = DRYAnalyzer(rj)
    loops = LoopOptimizer(rj)

    dry_issues = dry.find_all_issues()
    loop_issues = loops.find_all_issues()

    lines = [
        "# Code Optimization Report",
        "",
        f"Generated for: `{rj.root}`",
        "",
        "## Summary",
        "",
        f"- **DRY violations:** {len(dry_issues)}",
        f"- **Loop optimizations:** {len(loop_issues)}",
        f"- **Total opportunities:** {len(dry_issues) + len(loop_issues)}",
        "",
    ]

    # DRY Section
    lines.extend([
        "## DRY Violations",
        "",
    ])

    if dry_issues:
        for opt_type, issues in dry_issues.group_by_type().items():
            lines.append(f"### {opt_type.name.replace('_', ' ').title()}")
            lines.append("")
            for issue in issues:
                lines.append(f"- `{issue.location}`: {issue.message}")
            lines.append("")
    else:
        lines.append("No DRY violations found.")
        lines.append("")

    # Loop Section
    lines.extend([
        "## Loop Optimizations",
        "",
    ])

    if loop_issues:
        for opt_type, issues in loop_issues.group_by_type().items():
            lines.append(f"### {opt_type.name.replace('_', ' ').title()}")
            lines.append("")
            for issue in issues:
                lines.append(f"**{issue.location}**")
                lines.append("")
                lines.append("```python")
                lines.append(f"# Before:")
                lines.append(issue.original_code)
                lines.append("")
                lines.append(f"# After:")
                lines.append(issue.suggested_code)
                lines.append("```")
                lines.append("")
    else:
        lines.append("No loop optimizations found.")
        lines.append("")

    return "\n".join(lines)


rj = Rejig("src/")
report = generate_markdown_report(rj)
print(report)

# Or save to file
with open("optimization-report.md", "w") as f:
    f.write(report)
```

### JSON Export

```python
import json
from pathlib import Path

def export_to_json(rj: Rejig, output_path: str):
    """Export optimization findings to JSON."""
    dry = DRYAnalyzer(rj)
    loops = LoopOptimizer(rj)

    dry_issues = dry.find_all_issues()
    loop_issues = loops.find_all_issues()

    data = {
        "root": str(rj.root),
        "summary": {
            "dry_violations": len(dry_issues),
            "loop_optimizations": len(loop_issues),
            "total": len(dry_issues) + len(loop_issues),
        },
        "dry_issues": dry_issues.to_list_of_dicts(),
        "loop_issues": loop_issues.to_list_of_dicts(),
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"Exported to {output_path}")


rj = Rejig("src/")
export_to_json(rj, "optimization-findings.json")
```

### HTML Report

```python
def generate_html_report(rj: Rejig) -> str:
    """Generate an HTML report with syntax highlighting."""
    dry = DRYAnalyzer(rj)
    loops = LoopOptimizer(rj)

    dry_issues = dry.find_all_issues()
    loop_issues = loops.find_all_issues()

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Optimization Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 2em; }}
        .issue {{ border: 1px solid #ddd; padding: 1em; margin: 1em 0; border-radius: 4px; }}
        .location {{ color: #666; font-family: monospace; }}
        .code {{ background: #f5f5f5; padding: 1em; border-radius: 4px; overflow-x: auto; }}
        pre {{ margin: 0; }}
        h2 {{ color: #333; }}
        .count {{ color: #888; font-weight: normal; }}
    </style>
</head>
<body>
    <h1>Code Optimization Report</h1>
    <p>Path: <code>{rj.root}</code></p>

    <h2>Summary</h2>
    <ul>
        <li>DRY violations: {len(dry_issues)}</li>
        <li>Loop optimizations: {len(loop_issues)}</li>
    </ul>

    <h2>Loop Optimizations <span class="count">({len(loop_issues)})</span></h2>
"""

    for issue in loop_issues:
        html += f"""
    <div class="issue">
        <div class="location">{issue.location}</div>
        <p>{issue.message}</p>
        <div class="code">
            <pre><code># Before:
{issue.original_code}

# After:
{issue.suggested_code}</code></pre>
        </div>
    </div>
"""

    html += """
</body>
</html>
"""
    return html


rj = Rejig("src/")
html = generate_html_report(rj)
with open("report.html", "w") as f:
    f.write(html)
```

## CI Integration

### Pre-commit Hook

```python
#!/usr/bin/env python3
"""Pre-commit hook for optimization checks."""

import subprocess
import sys
from pathlib import Path

from rejig import Rejig, DRYAnalyzer, LoopOptimizer

def get_staged_files():
    """Get list of staged Python files."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True
    )
    return [f for f in result.stdout.splitlines() if f.endswith(".py")]


def check_files(files: list[str]) -> int:
    """Check staged files for optimization issues."""
    if not files:
        return 0

    rj = Rejig(".")
    loops = LoopOptimizer(rj)

    issues_found = 0

    for file_path in files:
        path = Path(file_path)
        file_issues = loops.find_all_issues(min_confidence=0.9).in_file(path)

        if file_issues:
            print(f"\n{file_path}:")
            for issue in file_issues:
                print(f"  Line {issue.line_number}: {issue.message}")
                issues_found += 1

    return issues_found


if __name__ == "__main__":
    files = get_staged_files()
    issues = check_files(files)

    if issues:
        print(f"\nFound {issues} optimization issues. Consider fixing before commit.")
        sys.exit(1)

    sys.exit(0)
```

### GitHub Action

```yaml
# .github/workflows/optimize.yml
name: Code Optimization Check

on:
  pull_request:
    paths:
      - '**.py'

jobs:
  optimize:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install rejig

      - name: Run optimization check
        run: |
          python - << 'EOF'
          from rejig import Rejig, LoopOptimizer

          rj = Rejig("src/")
          loops = LoopOptimizer(rj)

          issues = loops.find_all_issues(min_confidence=0.9)

          if issues:
              print("::warning::Found optimization opportunities:")
              for issue in issues:
                  print(f"::warning file={issue.file_path},line={issue.line_number}::{issue.message}")
          EOF
```

## Interactive Analysis

### REPL Exploration

```python
# Start Python REPL and explore interactively
from rejig import Rejig, DRYAnalyzer, LoopOptimizer

rj = Rejig("src/")
dry = DRYAnalyzer(rj)
loops = LoopOptimizer(rj)

# Explore DRY issues
dry_issues = dry.find_all_issues()
print(dry_issues.summary())

# Drill into specific types
duplicates = dry_issues.dry_issues()
for d in duplicates[:5]:
    print(f"{d.location}: {d.message}")

# Explore loop issues
loop_issues = loops.find_all_issues()

# Filter to specific file
file_issues = loop_issues.in_file("src/utils.py")

# Get suggestions
for issue in file_issues:
    print(f"Line {issue.line_number}:")
    print(f"  Current: {issue.original_code}")
    print(f"  Better:  {issue.suggested_code}")
```
