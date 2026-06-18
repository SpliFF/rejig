"""Rejig CLI - command-line interface for code analysis and refactoring.

Usage:
    rejig analyze <path>     Run code analysis (complexity, dead code, patterns)
    rejig security <path>    Run security scan
    rejig todos <path>       List TODO/FIXME comments
    rejig imports <path>     Analyze imports (unused, circular)
    rejig modernize <path>   Show/apply modernization opportunities
    rejig split <path>       Analyze files for splitting
    rejig metrics <path>     Show code metrics
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _make_rejig(path: str, dry_run: bool = False):
    """Create a Rejig instance, handling import errors gracefully."""
    from rejig import Rejig
    return Rejig(path, dry_run=dry_run)


def cmd_analyze(args: argparse.Namespace) -> int:
    """Run code analysis."""
    rj = _make_rejig(args.path)
    report = rj.analyze_code()

    if args.format == "json":
        print(json.dumps(report, indent=2, default=str))
        return 0

    if isinstance(report, dict):
        for section, items in report.items():
            print(f"\n=== {section} ===")
            if isinstance(items, list):
                for item in items:
                    print(f"  {item}")
            else:
                print(f"  {items}")
    else:
        print(report)
    return 0


def cmd_security(args: argparse.Namespace) -> int:
    """Run security scan."""
    rj = _make_rejig(args.path)
    report = rj.analyze_security()

    if args.format == "json":
        print(json.dumps(report, indent=2, default=str))
        return 0

    if isinstance(report, dict):
        findings = report.get("findings", [])
        if not findings:
            print("No security issues found.")
            return 0
        for finding in findings:
            print(f"  [{finding.get('severity', '?')}] {finding.get('message', finding)}")
    else:
        print(report)
    return 0


def cmd_todos(args: argparse.Namespace) -> int:
    """List TODO/FIXME comments."""
    rj = _make_rejig(args.path)
    result = rj.find_todos()

    if args.format == "json":
        todos = []
        if hasattr(result, "targets"):
            for t in result.targets:
                todos.append({
                    "file": str(getattr(t, "file_path", "")),
                    "line": getattr(t, "line_number", 0),
                    "text": getattr(t, "text", str(t)),
                })
        print(json.dumps(todos, indent=2))
        return 0

    if hasattr(result, "targets"):
        if not result.targets:
            print("No TODOs found.")
            return 0
        for t in result.targets:
            file_path = getattr(t, "file_path", "")
            line = getattr(t, "line_number", "?")
            text = getattr(t, "text", str(t))
            print(f"  {file_path}:{line}: {text}")
    else:
        print(result)
    return 0


def cmd_imports(args: argparse.Namespace) -> int:
    """Analyze imports."""
    rj = _make_rejig(args.path)

    print("=== Unused Imports ===")
    unused = rj.find_unused_imports()
    if hasattr(unused, "targets"):
        for t in unused.targets:
            print(f"  {t}")
    elif isinstance(unused, list):
        for item in unused:
            print(f"  {item}")
    else:
        print(f"  {unused}")

    print("\n=== Circular Imports ===")
    try:
        circular = rj.find_circular_imports()
        if hasattr(circular, "__iter__") and not isinstance(circular, str):
            found = False
            for item in circular:
                print(f"  {item}")
                found = True
            if not found:
                print("  None found.")
        else:
            print(f"  {circular}")
    except Exception as e:
        print(f"  Error: {e}")

    return 0


def cmd_modernize(args: argparse.Namespace) -> int:
    """Show/apply modernization opportunities."""
    rj = _make_rejig(args.path, dry_run=args.dry_run)
    result = rj.modernize_all_files()

    if args.format == "json":
        print(json.dumps({"success": result.success, "message": result.message}, indent=2))
        return 0

    print(result.message)
    if result.files_changed:
        for f in result.files_changed:
            print(f"  Modified: {f}")
    return 0


def cmd_split(args: argparse.Namespace) -> int:
    """Analyze files for splitting."""
    rj = _make_rejig(args.path)

    try:
        analyzer = rj.get_split_analyzer()
    except AttributeError:
        # Fallback: find long files
        result = rj.find_long_files(min_lines=args.min_lines)
        if hasattr(result, "targets"):
            for t in result.targets:
                print(f"  {t}")
        else:
            print(result)
        return 0

    for file_path in rj.files:
        result = analyzer.analyze(file_path)
        if result and getattr(result, "should_split", False):
            print(f"  {file_path}: {result}")
    return 0


def cmd_metrics(args: argparse.Namespace) -> int:
    """Show code metrics."""
    rj = _make_rejig(args.path)
    summary = rj.get_code_metrics_summary()

    if args.format == "json":
        print(json.dumps(summary, indent=2, default=str))
        return 0

    if isinstance(summary, dict):
        for key, value in summary.items():
            print(f"  {key}: {value}")
    else:
        print(summary)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="rejig",
        description="Rejig - programmatic code refactoring and analysis",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Common arguments
    def add_common_args(sub):
        sub.add_argument("path", nargs="?", default=".", help="Path to analyze (default: current directory)")
        sub.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    # analyze
    p = subparsers.add_parser("analyze", help="Run code analysis")
    add_common_args(p)

    # security
    p = subparsers.add_parser("security", help="Run security scan")
    add_common_args(p)

    # todos
    p = subparsers.add_parser("todos", help="List TODO/FIXME comments")
    add_common_args(p)

    # imports
    p = subparsers.add_parser("imports", help="Analyze imports")
    add_common_args(p)

    # modernize
    p = subparsers.add_parser("modernize", help="Modernize code")
    add_common_args(p)
    p.add_argument("--dry-run", action="store_true", default=True, help="Preview changes (default)")
    p.add_argument("--no-dry-run", action="store_false", dest="dry_run", help="Apply changes")

    # split
    p = subparsers.add_parser("split", help="Analyze files for splitting")
    add_common_args(p)
    p.add_argument("--min-lines", type=int, default=500, help="Minimum lines to flag (default: 500)")

    # metrics
    p = subparsers.add_parser("metrics", help="Show code metrics")
    add_common_args(p)

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "analyze": cmd_analyze,
        "security": cmd_security,
        "todos": cmd_todos,
        "imports": cmd_imports,
        "modernize": cmd_modernize,
        "split": cmd_split,
        "metrics": cmd_metrics,
    }

    try:
        return commands[args.command](args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
