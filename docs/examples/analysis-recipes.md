# Analysis Recipes

Ready-to-use scripts for analyzing your Python codebase.

## Quick Audit Script

```python
#!/usr/bin/env python
"""Quick codebase audit script."""
from rejig import Rejig, DRYAnalyzer, LoopOptimizer

def audit(path: str = "src/") -> None:
    rj = Rejig(path)

    # Get all issues
    report = rj.analyze_code()
    security = rj.find_security_issues()

    # Summary
    print("=" * 60)
    print("CODEBASE AUDIT REPORT")
    print("=" * 60)
    print()

    # Analysis issues
    print("Code Analysis:")
    print(f"  Total issues: {report.total_issues}")
    for label, findings in (
        ("Complexity", report.complexity_issues),
        ("Patterns", report.pattern_issues),
        ("Dead code", report.dead_code),
    ):
        if findings:
            print(f"  {label}: {len(findings)}")
            for issue in findings.sorted_by_severity()[:3]:
                print(f"    - {issue.file_path}:{issue.line_number}")
                print(f"      {issue.type.name}: {issue.message}")

    # Security issues
    print("\nSecurity:")
    print(f"  {security.summary()}")
    critical = security.critical()
    high = security.high()
    if critical or high:
        print("\n  Critical/High Issues:")
        for issue in list(critical)[:5] + list(high)[:5]:
            print(f"    - [{issue.severity}] {issue.file_path}:{issue.line_number}")
            print(f"      {issue.message}")

    # Optimization opportunities
    dry = DRYAnalyzer(rj).find_all_issues()
    loops = LoopOptimizer(rj).find_all_issues()
    print("\nOptimization Opportunities:")
    print(f"  Total: {len(dry) + len(loops)} findings")
    for label, findings in (("DRY", dry), ("Loops", loops)):
        by_type = findings.count_by_type()
        for opt_type, count in sorted(by_type.items(), key=lambda x: -x[1])[:3]:
            print(f"    {label} {opt_type.name}: {count}")

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

    # find_complex_functions returns an AnalysisTargetList; each finding's
    # `value` holds the measured cyclomatic complexity.
    complex_funcs = analyzer.find_complex_functions(max_complexity=threshold)

    if not complex_funcs:
        print("No functions exceed complexity threshold.")
        return

    print(f"Found {len(complex_funcs)} complex functions:\n")

    # Group by file
    by_file = {}
    for finding in complex_funcs:
        file_path = str(finding.file_path)
        by_file.setdefault(file_path, []).append(finding)

    for file_path, findings in sorted(by_file.items()):
        print(f"{file_path}")
        for finding in sorted(findings, key=lambda f: -(f.value or 0)):
            print(f"  {finding.name}:")
            print(f"    Cyclomatic: {finding.value}")
            print(f"    {finding.message}")
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
        print(f"  [{func.severity}] {func.file_path}:{func.line_number} - {func.name}")
    if len(unused_funcs) > 10:
        print(f"  ... and {len(unused_funcs) - 10} more")
    print()

    # Unused classes
    unused_classes = analyzer.find_unused_classes()
    print(f"Unused Classes: {len(unused_classes)}")
    for cls in unused_classes[:10]:
        print(f"  {cls.file_path}:{cls.line_number} - {cls.name}")
    print()

    # Unused imports (provided by the Rejig facade, not DeadCodeAnalyzer)
    unused_imports = rj.find_unused_imports()
    print(f"Unused Imports: {len(unused_imports)}")
    by_file = {}
    for imp in unused_imports:
        file_path = str(imp.file_path)
        by_file.setdefault(file_path, []).append(imp)

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
from collections import defaultdict
from rejig import Rejig

def type_coverage(path: str = "src/") -> None:
    rj = Rejig(path)

    # All module-level functions, and those missing a return annotation.
    all_funcs = rj.find_functions()
    untyped = rj.find_functions_without_type_hints()

    total = len(all_funcs)
    missing = len(untyped)
    typed = max(total - missing, 0)
    coverage = (typed / total * 100) if total else 100.0

    print("TYPE HINT COVERAGE REPORT")
    print("=" * 60)
    print()
    print(f"Overall Coverage: {coverage:.1f}%")
    print(f"Functions: {typed}/{total} typed")
    print()

    # Group the untyped findings by file
    by_file = defaultdict(list)
    for finding in untyped:
        by_file[str(finding.file_path)].append(finding)

    print("Files With Untyped Functions:")
    print("-" * 40)
    for file_path, findings in sorted(by_file.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"  {len(findings):3d} untyped | {file_path}")
        for finding in findings[:3]:
            print(f"      - {finding.name} (line {finding.line_number})")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "src/"
    type_coverage(path)
```

## Docstring Coverage

```python
#!/usr/bin/env python
"""Check docstring coverage."""
from collections import defaultdict
from rejig import Rejig

def docstring_coverage(path: str = "src/") -> None:
    rj = Rejig(path)

    # All functions/classes that lack a docstring.
    missing = rj.find_missing_docstrings()

    print("DOCSTRING COVERAGE REPORT")
    print("=" * 60)
    print()
    print(f"Items missing docstrings: {len(missing)}")
    print()

    # Missing by file
    missing_by_file = defaultdict(list)
    for target in missing:
        missing_by_file[str(target.file_path)].append(target.name)

    print("Files Missing Docstrings:")
    for file_path, names in sorted(missing_by_file.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"  {file_path}: {len(names)} missing")
        for name in names[:3]:
            print(f"    - {name}")
        if len(names) > 3:
            print(f"    ... and {len(names) - 3} more")

    # Also surface docstrings that no longer match their signatures.
    outdated = rj.find_outdated_docstrings()
    print()
    print(f"Outdated docstrings: {len(outdated)}")
    for item in outdated[:5]:
        print(f"  {item['file_path']}:{item['name']}")
        if item["stale_params"]:
            print(f"    Stale params: {item['stale_params']}")
        if item["missing_params"]:
            print(f"    Missing params: {item['missing_params']}")

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
    by_type = defaultdict(int)
    for todo in todos:
        by_type[todo.todo_type] += 1
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
    high_priority = todos.high_priority()
    if high_priority:
        print(f"High Priority ({len(high_priority)}):")
        for todo in high_priority[:10]:
            print(f"  [{todo.todo_type}] {todo.file_path}:{todo.line_number}")
            print(f"    {todo.todo_text[:60]}...")
    print()

    # Without issue refs
    no_issues = todos.without_issues()
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
    modules = graph.get_modules()
    edges = graph.get_edges()
    print(f"Total modules: {len(modules)}")
    print(f"Total import edges: {len(edges)}")
    print()

    # Circular imports
    cycles = graph.find_circular_imports()
    print(f"Circular Imports: {len(cycles)}")
    for i, cycle in enumerate(cycles[:5], 1):
        print(f"  {i}. {' -> '.join(cycle.cycle)}")
    if len(cycles) > 5:
        print(f"  ... and {len(cycles) - 5} more")
    print()

    # Most imported modules (by number of dependents)
    print("Most Imported Modules:")
    most_imported = sorted(
        ((m, len(graph.get_dependents(m))) for m in modules),
        key=lambda x: -x[1],
    )[:10]
    for module, count in most_imported:
        print(f"  {module}: imported by {count} modules")
    print()

    # Modules with most imports (by number of dependencies)
    print("Modules with Most Dependencies:")
    most_deps = sorted(
        ((m, len(graph.get_dependencies(m))) for m in modules),
        key=lambda x: -x[1],
    )[:10]
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
from rejig import (
    Rejig,
    CodeMetrics,
    ComplexityAnalyzer,
    DeadCodeAnalyzer,
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

    # Code metrics (get_project_summary returns a dict)
    summary = CodeMetrics(rj).get_project_summary()
    report["metrics"] = {
        "files": summary["total_files"],
        "total_loc": summary["total_lines"],
        "functions": summary["total_functions"],
        "classes": summary["total_classes"],
        "avg_complexity": summary["avg_complexity"],
    }

    # Type hints: count functions missing a return annotation
    total_funcs = len(rj.find_functions())
    untyped = len(rj.find_functions_without_type_hints())
    typed = max(total_funcs - untyped, 0)
    report["type_hints"] = {
        "coverage_percent": (typed / total_funcs * 100) if total_funcs else 100.0,
        "typed_functions": typed,
        "total_functions": total_funcs,
    }

    # Docstrings
    missing_docs = rj.find_missing_docstrings()
    report["docstrings"] = {
        "missing": len(missing_docs),
        "outdated": len(rj.find_outdated_docstrings()),
    }

    # Complexity (findings carry the measured complexity in `value`)
    complex_funcs = ComplexityAnalyzer(rj).find_complex_functions(max_complexity=10)
    report["complexity"] = {
        "functions_over_threshold": len(complex_funcs),
        "top_5": [
            {"name": f.name, "file": str(f.file_path), "complexity": f.value}
            for f in complex_funcs[:5]
        ],
    }

    # Dead code
    dead_analyzer = DeadCodeAnalyzer(rj)
    report["dead_code"] = {
        "unused_functions": len(dead_analyzer.find_unused_functions()),
        "unused_classes": len(dead_analyzer.find_unused_classes()),
        "unused_imports": len(rj.find_unused_imports()),
    }

    # Security (enum keys stringified for JSON)
    security = rj.find_security_issues()
    report["security"] = {
        "total": len(security),
        "by_severity": security.count_by_severity(),
        "by_type": {k.name: v for k, v in security.count_by_type().items()},
    }

    # Analysis
    analysis = rj.analyze_code()
    report["analysis"] = {
        "total": analysis.total_issues,
        "complexity": len(analysis.complexity_issues or []),
        "patterns": len(analysis.pattern_issues or []),
        "dead_code": len(analysis.dead_code or []),
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
    print(f"Missing docstrings: {report['docstrings']['missing']}")
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
    max_missing_docstrings: int = 50,
    fail_on_security: bool = True,
) -> int:
    rj = Rejig(path)
    failed = False

    # Security check
    if fail_on_security:
        security = rj.find_security_issues()
        critical_high = list(security.critical()) + list(security.high())
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
    complex_funcs = analyzer.find_complex_functions(max_complexity=max_complexity)
    if complex_funcs:
        print(f"FAIL: {len(complex_funcs)} functions exceed complexity {max_complexity}")
        failed = True
    else:
        print(f"PASS: No functions exceed complexity {max_complexity}")

    # Type coverage check
    total_funcs = len(rj.find_functions())
    untyped = len(rj.find_functions_without_type_hints())
    typed = max(total_funcs - untyped, 0)
    coverage = (typed / total_funcs * 100) if total_funcs else 100.0
    if coverage < min_type_coverage:
        print(f"FAIL: Type hint coverage {coverage:.1f}% < {min_type_coverage}%")
        failed = True
    else:
        print(f"PASS: Type hint coverage {coverage:.1f}%")

    # Docstring check
    missing = len(rj.find_missing_docstrings())
    if missing > max_missing_docstrings:
        print(f"FAIL: {missing} items missing docstrings (> {max_missing_docstrings})")
        failed = True
    else:
        print(f"PASS: {missing} items missing docstrings")

    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(ci_check())
```
