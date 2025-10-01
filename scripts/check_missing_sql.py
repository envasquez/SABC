#!/usr/bin/env python3
"""Check for missing SQL queries in query service calls.

This script detects cases where qs.fetch_all() or qs.fetch_one() is called
with only a dict parameter, which indicates the SQL query string was removed.
"""

import re
import sys
from pathlib import Path


def check_file(file_path: Path) -> list[tuple[int, str]]:
    """Check a single Python file for missing SQL queries.

    Returns list of (line_number, line_content) tuples for problematic lines.
    """
    issues = []
    content = file_path.read_text()
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        # Look for qs.fetch_all( or qs.fetch_one( followed by only a dict
        # Pattern: qs.fetch_X( followed by whitespace and {
        if re.search(r"qs\.fetch_(all|one)\(\s*\{", line):
            issues.append((i, line.strip()))

    return issues


def main():
    """Scan all Python files in routes/ for missing SQL queries."""
    routes_dir = Path(__file__).parent.parent / "routes"
    all_issues = []

    print("🔍 Checking for missing SQL queries in query service calls...")
    print("=" * 70)

    for py_file in routes_dir.rglob("*.py"):
        issues = check_file(py_file)
        if issues:
            all_issues.extend([(py_file, line_num, line) for line_num, line in issues])

    if all_issues:
        print(f"\n❌ Found {len(all_issues)} potential missing SQL queries:\n")
        for file_path, line_num, line in all_issues:
            rel_path = file_path.relative_to(Path.cwd())
            print(f"  {rel_path}:{line_num}")
            print(f"    {line}")
            print()
        print("These calls are missing SQL query strings!")
        print('They should be: qs.fetch_X("SQL HERE", {params})')
        return 1
    else:
        print("\n✅ No missing SQL queries detected!")
        print("\nAll qs.fetch_all() and qs.fetch_one() calls appear correct.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
