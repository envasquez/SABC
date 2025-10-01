#!/usr/bin/env python3
"""Aggressively strip comments, docstrings, and blank lines from Python files."""

from pathlib import Path


def strip_file(filepath: Path) -> tuple[int, int]:
    """Strip comments and blank lines. Returns (original_lines, new_lines)."""
    with open(filepath) as f:
        lines = f.readlines()
    original_count = len(lines)

    result = []
    in_docstring = False
    docstring_char = None
    skip_next_blank = False

    for line in lines:
        stripped = line.strip()

        # Handle docstrings
        if '"""' in line or "'''" in line:
            quote = '"""' if '"""' in line else "'''"
            if not in_docstring:
                in_docstring = True
                docstring_char = quote
                if line.count(quote) == 2:  # Single line docstring
                    in_docstring = False
                continue
            elif quote == docstring_char:
                in_docstring = False
                continue

        if in_docstring:
            continue

        # Skip comment-only lines
        if stripped.startswith("#"):
            continue

        # Remove inline comments but keep strings with #
        if "#" in line and not any(q in line.split("#")[0] for q in ['"', "'"]):
            line = line.split("#")[0].rstrip() + "\n"

        # Skip excessive blank lines
        if not stripped:
            if skip_next_blank or not result or not result[-1].strip():
                continue
            skip_next_blank = True
        else:
            skip_next_blank = False

        result.append(line)

    # Remove trailing blank lines
    while result and not result[-1].strip():
        result.pop()

    if result:
        result.append("\n")

    with open(filepath, "w") as f:
        f.writelines(result)

    return original_count, len(result)


def main():
    repo_root = Path(__file__).parent.parent
    exclude_dirs = {"__pycache__", ".git", "venv", ".nix-profile", "tests", "node_modules"}

    total_before = 0
    total_after = 0
    files_processed = 0

    for py_file in repo_root.rglob("*.py"):
        if any(excluded in py_file.parts for excluded in exclude_dirs):
            continue
        if py_file.name == "strip_comments.py":
            continue

        before, after = strip_file(py_file)
        total_before += before
        total_after += after
        files_processed += 1
        reduction = before - after
        if reduction > 0:
            print(f"✂️  {py_file.relative_to(repo_root)}: {before} → {after} (-{reduction})")

    print(f"\n📊 Total: {total_before} → {total_after} lines")
    print(f"   Reduced by {total_before - total_after} lines ({files_processed} files)")
    print(f"   {100 * (total_before - total_after) / total_before:.1f}% reduction")


if __name__ == "__main__":
    main()
