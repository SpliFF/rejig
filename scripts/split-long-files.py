#!/usr/bin/env python3
"""Split long Python files into modules using rejig.

This script identifies Python files over a specified line threshold and
splits them into package directories with one file per class.

Usage:
    python scripts/split-long-files.py [--min-lines N] [--dry-run] [path]

Examples:
    # Find and report long files (dry-run by default)
    python scripts/split-long-files.py src/rejig

    # Actually perform the splits
    python scripts/split-long-files.py src/rejig --no-dry-run

    # Custom threshold
    python scripts/split-long-files.py src/rejig --min-lines 300
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rejig import Rejig


def main():
    parser = argparse.ArgumentParser(
        description="Find and split long Python files using rejig",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="src/rejig",
        help="Path to analyze (default: src/rejig)",
    )
    parser.add_argument(
        "--min-lines",
        type=int,
        default=500,
        help="Minimum lines to consider a file 'long' (default: 500)",
    )
    parser.add_argument(
        "--min-classes",
        type=int,
        default=2,
        help="Minimum classes to consider splitting by class (default: 2)",
    )
    parser.add_argument(
        "--min-functions",
        type=int,
        default=3,
        help="Minimum functions to consider splitting by function (default: 3)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview changes without modifying files (default: True)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually perform the splits",
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="Perform splits on eligible files (respects --dry-run)",
    )

    args = parser.parse_args()

    # Handle dry-run logic
    dry_run = not args.no_dry_run

    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path does not exist: {path}")
        sys.exit(1)

    print(f"Analyzing Python files in: {path}")
    print(f"Minimum lines threshold: {args.min_lines}")
    print(f"Minimum classes to split: {args.min_classes}")
    print(f"Minimum functions to split: {args.min_functions}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("-" * 60)

    # Initialize rejig
    rj = Rejig(path, dry_run=dry_run)

    # Get split analyzer with configured parameters
    analyzer = rj.get_split_analyzer(
        min_lines=args.min_lines,
        min_classes_to_split=args.min_classes,
        min_functions_to_split=args.min_functions,
    )

    # Get all long files analysis
    analyses = analyzer.find_long_files_analysis()

    if not analyses:
        print(f"No files found with >= {args.min_lines} lines")
        return

    print(f"\nFound {len(analyses)} files with >= {args.min_lines} lines:\n")

    # Separate splittable from not splittable
    splittable = [a for a in analyses if a.can_split]
    not_splittable = [a for a in analyses if not a.can_split]

    # Report findings
    print("=" * 60)
    print("SPLITTABLE FILES")
    print("=" * 60)

    for analysis in splittable:
        rel_path = analysis.file_path.relative_to(path) if analysis.file_path.is_relative_to(path) else analysis.file_path
        print(f"\n{rel_path}")
        print(f"  Lines: {analysis.total_lines}")
        print(f"  Classes: {analysis.class_count}, Functions: {analysis.function_count}")
        print(f"  Split by: {analysis.split_by}")
        print(f"  Reason: {analysis.reason}")

    if not_splittable:
        print("\n" + "=" * 60)
        print("NOT EASILY SPLITTABLE")
        print("=" * 60)

        for analysis in not_splittable:
            rel_path = analysis.file_path.relative_to(path) if analysis.file_path.is_relative_to(path) else analysis.file_path
            print(f"\n{rel_path}")
            print(f"  Lines: {analysis.total_lines}")
            print(f"  Classes: {analysis.class_count}, Functions: {analysis.function_count}")
            print(f"  Reason: {analysis.reason}")

    # Summary
    summary = analyzer.get_summary()
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total long files: {summary['total_long_files']}")
    print(f"Splittable: {summary['splittable_count']}")
    print(f"  - By class: {summary['splittable_by_class']}")
    print(f"  - By function: {summary['splittable_by_function']}")
    print(f"Not easily splittable: {summary['not_splittable_count']}")
    print(f"Total lines in long files: {summary['total_lines_in_long_files']:,}")

    # Perform splits if requested
    if args.split and splittable:
        print("\n" + "=" * 60)
        print("PERFORMING SPLITS" + (" (DRY RUN)" if dry_run else ""))
        print("=" * 60)

        for analysis in splittable:
            file_target = rj.file(analysis.file_path)
            split_by = analysis.split_by

            print(f"\nSplitting {analysis.file_path.name} by {split_by}...")
            result = file_target.split(by=split_by)

            if result.success:
                print(f"  {result.message}")
                if result.files_changed:
                    print(f"  Files that would be created/modified:")
                    for f in result.files_changed[:10]:  # Show first 10
                        print(f"    - {f.name}")
                    if len(result.files_changed) > 10:
                        print(f"    ... and {len(result.files_changed) - 10} more")
            else:
                print(f"  ERROR: {result.message}")

    elif splittable and not args.split:
        print(f"\nTo split these files, run with --split flag")
        print(f"Example: python {sys.argv[0]} {path} --split")


if __name__ == "__main__":
    main()
