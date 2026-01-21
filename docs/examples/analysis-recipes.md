# Analysis Recipes

Ready-to-use scripts for analyzing your Python codebase.

## Quick Audit Script

```python
#!/usr/bin/env python
"""Quick codebase audit script."""
from rejig import Rejig

def audit(path: str = "src/") -> None:
    rj = Rejig(path)

    # Get all issues
    issues = rj.find_analysis_issues()
    security = rj.find_security_issues()
    optimization = rj.find_optimization_opportunities()

    # Summary
    print("=" * 60)
    print("CODEBASE AUDIT REPORT")
    print("=" * 60)
    print()

    # Analysis issues
    print("Code Analysis:")
    print(f"  {issues.summary()}")
    if issues.by_severity("high"):
        print("\n  High Priority:")
        for issue in issues.by_severity("high")[:5]:
            print(f"    - {issue.file_path}:{issue.line_number}")
            print(f"      {issue.type}: {issue.message}")

    # Security issues
    print("\nSecurity:")
    print(f"  {security.summary()}")
    if security.critical() or security.high():
        print("\n  Critical/High Issues:")
        for issue in (security.critical() + security.high())[:5]:
            print(f"    - [{issue.severity}] {issue.file_path}:{issue.line_number}")
            print(f"      {issue.message}")

    # Optimization opportunities
    print("\nOptimization Opportunities:")
    print(f"  Total: {len(optimization)} findings")
    by_type = optimization.count_by_type()
    for type_name, count in sorted(by_type.items(), key=lambda x: -x[1])[:5]:
        print(f"    {type_name}: {count}")

    print()
    print("=" * 60)

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "src/"
    audit(path)
```

## Complexity Report

```python
#!/usr/bin/env python
"""Generate complexity report."""
from rejig import Rejig, ComplexityAnalyzer

def complexity_report(path: str = "src/", threshold: int = 10) -> None:
    rj = Rejig(path)
    analyzer = ComplexityAnalyzer(rj)

    print("COMPLEXITY REPORT")
    print("=" * 60)
    print(f"Threshold: {threshold}")
    print()

    # Find complex functions
    complex_funcs = analyzer.find_complex_functions(threshold)

    if not complex_funcs:
        print("No functions exceed complexity threshold.")
        return

    print(f"Found {len(complex_funcs)} complex functions:\n")

    # Group by file
    by_file = {}
    for func, complexity in complex_funcs:
        file_path = str(func.file_path)
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append((func, complexity))

    for file_path, funcs in sorted(by_file.items()):
        print(f"{file_path}")
        for func, c in sorted(funcs, key=lambda x: -x[1].cyclomatic):
            print(f"  {func.name}:")
            print(f"    Cyclomatic: {c.cyclomatic}")
            print(f"    Nesting: {c.max_nesting}")
            print(f"    Lines: {c.lines}")
        print()

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "src/"
    complexity_report(path)
```

## Dead Code Finder

```python
#!/usr/bin/env python
"""Find potentially dead code."""
from rejig import Rejig, DeadCodeAnalyzer

def find_dead_code(path: str = "src/") -> None:
    rj = Rejig(path)
    analyzer = DeadCodeAnalyzer(rj)

    print("DEAD CODE ANALYSIS")
    print("=" * 60)
    print()

    # Unused functions
    unused_funcs = analyzer.find_unused_functions()
    print(f"Unused Functions: {len(unused_funcs)}")
    for func in unused_funcs[:10]:
        confidence_marker = {
            "high": "[!]",
            "medium": "[?]",
            "low": "[ ]",
        }.get(func.confidence, "[ ]")
        print(f"  {confidence_marker} {func.file_path}:{func.line_number} - {func.name}")
    if len(unused_funcs) > 10:
        print(f"  ... and {len(unused_funcs) - 10} more")
    print()

    # Unused classes
    unused_classes = analyzer.find_unused_classes()
    print(f"Unused Classes: {len(unused_classes)}")
    for cls in unused_classes[:10]:
        print(f"  {cls.file_path}:{cls.line_number} - {cls.name}")
    print()

    # Unused imports
    unused_imports = analyzer.find_unused_imports()
    print(f"Unused Imports: {len(unused_imports)}")
    by_file = {}
    for imp in unused_imports:
        file_path = str(imp.file_path)
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(imp)

    for file_path, imps in sorted(by_file.items())[:5]:
        print(f"  {file_path}: {len(imps)} unused imports")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "src/"
    find_dead_code(path)
```

## Type Hint Coverage

```python
#!/usr/bin/env python
"""Check type hint coverage."""
from rejig import Rejig, TypeHintAnalyzer

def type_coverage(path: str = "src/") -> None:
    rj = Rejig(path)
    analyzer = TypeHintAnalyzer(rj)

    stats = analyzer.coverage_stats()

    print("TYPE HINT COVERAGE REPORT")
    print("=" * 60)
    print()
    print(f"Overall Coverage: {stats.coverage_percent:.1f}%")
    print()
    print(f"Functions: {stats.typed_functions}/{stats.total_functions} typed")
    print(f"Methods: {stats.typed_methods}/{stats.total_methods} typed")
    print()

    # Coverage by file
    print("Coverage by File:")
    print("-" * 40)

    files = sorted(stats.by_file.items(), key=lambda x: x[1].coverage_percent)

    # Show lowest coverage files
    print("\nLowest Coverage:")
    for file_path, file_stats in files[:10]:
        bar = "#" * int(file_stats.coverage_percent / 5)
        print(f"  {file_stats.coverage_percent:5.1f}% |{bar:<20}| {file_path}")

    print("\nHighest Coverage:")
    for file_path, file_stats in files[-10:]:
        bar = "#" * int(file_stats.coverage_percent / 5)
        print(f"  {file_stats.coverage_percent:5.1f}% |{bar:<20}| {file_path}")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "src/"
    type_coverage(path)
```

## Docstring Coverage

```python
#!/usr/bin/env python
"""Check docstring coverage."""
from rejig import Rejig, DocstringAnalyzer

def docstring_coverage(path: str = "src/") -> None:
    rj = Rejig(path)
    analyzer = DocstringAnalyzer(rj)

    report = analyzer.analyze()

    print("DOCSTRING COVERAGE REPORT")
    print("=" * 60)
    print()
    print(f"Overall Coverage: {report.coverage_percent:.1f}%")
    print()
    print(f"Total functions/methods: {report.total_functions}")
    print(f"With docstrings: {report.with_docstrings}")
    print(f"Missing docstrings: {report.total_functions - report.with_docstrings}")
    print()

    # Style breakdown
    print("Docstring Styles:")
    for style, count in sorted(report.styles.items(), key=lambda x: -x[1]):
        print(f"  {style}: {count}")
    print()

    # Missing by file
    print("Files Missing Docstrings:")
    missing_by_file = report.missing_by_file()
    for file_path, missing in sorted(missing_by_file.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"  {file_path}: {len(missing)} missing")
        for func_name in missing[:3]:
            print(f"    - {func_name}")
        if len(missing) > 3:
            print(f"    ... and {len(missing) - 3} more")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "src/"
    docstring_coverage(path)
```

## TODO Tracker

```python
#!/usr/bin/env python
"""Track TODO comments in codebase."""
from rejig import Rejig
from collections import defaultdict

def track_todos(path: str = "src/") -> None:
    rj = Rejig(path)
    todos = rj.find_todos()

    print("TODO TRACKING REPORT")
    print("=" * 60)
    print()
    print(f"Total TODOs: {len(todos)}")
    print()

    # By type
    by_type = todos.count_by_type()
    print("By Type:")
    for todo_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {todo_type}: {count}")
    print()

    # By author (if available)
    by_author = defaultdict(list)
    for todo in todos:
        author = todo.author or "unassigned"
        by_author[author].append(todo)

    print("By Author:")
    for author, author_todos in sorted(by_author.items(), key=lambda x: -len(x[1])):
        print(f"  {author}: {len(author_todos)}")
    print()

    # High priority
    high_priority = todos.by_priority(1) + todos.by_priority(2)
    if high_priority:
        print(f"High Priority ({len(high_priority)}):")
        for todo in high_priority[:10]:
            print(f"  [{todo.todo_type}] {todo.file_path}:{todo.line_number}")
            print(f"    {todo.text[:60]}...")
    print()

    # Without issue refs
    no_issues = todos.without_issue_refs()
    print(f"Without Issue References: {len(no_issues)}")
    if no_issues:
        print("  Consider linking these to issues for tracking:")
        for todo in no_issues[:5]:
            print(f"    - {todo.file_path}:{todo.line_number}")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "src/"
    track_todos(path)
```

## Import Graph Analysis

```python
#!/usr/bin/env python
"""Analyze import structure."""
from rejig import Rejig, ImportGraph

def analyze_imports(path: str = "src/") -> None:
    rj = Rejig(path)
    graph = ImportGraph(rj)
    graph.build()

    print("IMPORT GRAPH ANALYSIS")
    print("=" * 60)
    print()

    # Basic stats
    print(f"Total modules: {graph.module_count}")
    print(f"Total import edges: {graph.edge_count}")
    print()

    # Circular imports
    cycles = graph.find_circular_imports()
    print(f"Circular Imports: {len(cycles)}")
    for i, cycle in enumerate(cycles[:5], 1):
        print(f"  {i}. {' -> '.join(cycle.modules)}")
    if len(cycles) > 5:
        print(f"  ... and {len(cycles) - 5} more")
    print()

    # Most imported modules
    print("Most Imported Modules:")
    most_imported = graph.most_imported(10)
    for module, count in most_imported:
        print(f"  {module}: imported by {count} modules")
    print()

    # Modules with most imports
    print("Modules with Most Dependencies:")
    most_deps = graph.most_dependencies(10)
    for module, count in most_deps:
        print(f"  {module}: imports {count} modules")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "src/"
    analyze_imports(path)
```

## Full Codebase Report

```python
#!/usr/bin/env python
"""Generate comprehensive codebase report."""
import json
from pathlib import Path
from rejig import (
    Rejig,
    CodeMetrics,
    TypeHintAnalyzer,
    DocstringAnalyzer,
    ComplexityAnalyzer,
    DeadCodeAnalyzer,
    SecurityReporter,
    AnalysisReporter,
)

def full_report(path: str = "src/", output: str = "report.json") -> None:
    rj = Rejig(path)

    report = {
        "path": str(path),
        "metrics": {},
        "type_hints": {},
        "docstrings": {},
        "complexity": {},
        "dead_code": {},
        "security": {},
        "analysis": {},
    }

    # Code metrics
    metrics = CodeMetrics(rj)
    project_metrics = metrics.analyze_project()
    report["metrics"] = {
        "files": project_metrics.file_count,
        "total_loc": project_metrics.total_loc,
        "functions": project_metrics.total_functions,
        "classes": project_metrics.total_classes,
        "avg_complexity": project_metrics.avg_complexity,
    }

    # Type hint coverage
    type_analyzer = TypeHintAnalyzer(rj)
    type_stats = type_analyzer.coverage_stats()
    report["type_hints"] = {
        "coverage_percent": type_stats.coverage_percent,
        "typed_functions": type_stats.typed_functions,
        "total_functions": type_stats.total_functions,
    }

    # Docstring coverage
    doc_analyzer = DocstringAnalyzer(rj)
    doc_report = doc_analyzer.analyze()
    report["docstrings"] = {
        "coverage_percent": doc_report.coverage_percent,
        "with_docstrings": doc_report.with_docstrings,
        "total": doc_report.total_functions,
    }

    # Complexity
    complexity_analyzer = ComplexityAnalyzer(rj)
    complex_funcs = complexity_analyzer.find_complex_functions(10)
    report["complexity"] = {
        "functions_over_threshold": len(complex_funcs),
        "top_5": [
            {"name": f.name, "file": str(f.file_path), "complexity": c.cyclomatic}
            for f, c in complex_funcs[:5]
        ],
    }

    # Dead code
    dead_analyzer = DeadCodeAnalyzer(rj)
    report["dead_code"] = {
        "unused_functions": len(dead_analyzer.find_unused_functions()),
        "unused_classes": len(dead_analyzer.find_unused_classes()),
        "unused_imports": len(dead_analyzer.find_unused_imports()),
    }

    # Security
    security = rj.find_security_issues()
    report["security"] = {
        "total": len(security),
        "by_severity": security.count_by_severity(),
        "by_type": security.count_by_type(),
    }

    # Analysis
    issues = rj.find_analysis_issues()
    report["analysis"] = {
        "total": len(issues),
        "by_severity": issues.count_by_severity(),
        "by_type": issues.count_by_type(),
    }

    # Save report
    with open(output, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Report saved to {output}")

    # Print summary
    print("\nSUMMARY")
    print("=" * 40)
    print(f"Files: {report['metrics']['files']}")
    print(f"Lines of code: {report['metrics']['total_loc']}")
    print(f"Type hint coverage: {report['type_hints']['coverage_percent']:.1f}%")
    print(f"Docstring coverage: {report['docstrings']['coverage_percent']:.1f}%")
    print(f"Security issues: {report['security']['total']}")
    print(f"Analysis issues: {report['analysis']['total']}")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "src/"
    output = sys.argv[2] if len(sys.argv) > 2 else "report.json"
    full_report(path, output)
```

## CI Integration Script

```python
#!/usr/bin/env python
"""CI integration script with configurable thresholds."""
import sys
from rejig import Rejig

def ci_check(
    path: str = "src/",
    max_complexity: int = 15,
    min_type_coverage: float = 80.0,
    min_doc_coverage: float = 70.0,
    fail_on_security: bool = True,
) -> int:
    rj = Rejig(path)
    failed = False

    # Security check
    if fail_on_security:
        security = rj.find_security_issues()
        critical_high = security.critical() + security.high()
        if critical_high:
            print(f"FAIL: {len(critical_high)} critical/high security issues")
            for issue in critical_high[:5]:
                print(f"  - {issue.file_path}:{issue.line_number}: {issue.message}")
            failed = True
        else:
            print("PASS: No critical/high security issues")

    # Complexity check
    from rejig import ComplexityAnalyzer
    analyzer = ComplexityAnalyzer(rj)
    complex_funcs = analyzer.find_complex_functions(max_complexity)
    if complex_funcs:
        print(f"FAIL: {len(complex_funcs)} functions exceed complexity {max_complexity}")
        failed = True
    else:
        print(f"PASS: No functions exceed complexity {max_complexity}")

    # Type coverage check
    from rejig import TypeHintAnalyzer
    type_analyzer = TypeHintAnalyzer(rj)
    type_stats = type_analyzer.coverage_stats()
    if type_stats.coverage_percent < min_type_coverage:
        print(f"FAIL: Type hint coverage {type_stats.coverage_percent:.1f}% < {min_type_coverage}%")
        failed = True
    else:
        print(f"PASS: Type hint coverage {type_stats.coverage_percent:.1f}%")

    # Docstring coverage check
    from rejig import DocstringAnalyzer
    doc_analyzer = DocstringAnalyzer(rj)
    doc_report = doc_analyzer.analyze()
    if doc_report.coverage_percent < min_doc_coverage:
        print(f"FAIL: Docstring coverage {doc_report.coverage_percent:.1f}% < {min_doc_coverage}%")
        failed = True
    else:
        print(f"PASS: Docstring coverage {doc_report.coverage_percent:.1f}%")

    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(ci_check())
```
