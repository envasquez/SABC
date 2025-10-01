#!/usr/bin/env python3
import re
from pathlib import Path


def compact_conditionals(content):
    content = re.sub(
        r'if\s+not\s+\(?\s*(\w+)\s*:=\s*(\w+\([^)]+\))\)?:\s+return\s+RedirectResponse\(["\']([^"\']+)["\']\)',
        r'if not (\1 := \2): return RedirectResponse("\3")',
        content,
    )
    content = re.sub(
        r"if isinstance\((\w+),\s*RedirectResponse\):\s+return \1",
        r"if isinstance(\1, RedirectResponse): return \1",
        content,
    )
    return content


def inline_simple_vars(content):
    lines = content.split("\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if i + 1 < len(lines):
            var_match = re.match(r"\s+(\w+)\s*=\s*(.+)", line)
            next_match = re.match(r"\s+return\s+(\w+)\s*$", lines[i + 1])
            if var_match and next_match and var_match.group(1) == next_match.group(1):
                result.append(line.replace(var_match.group(1) + " =", "return"))
                i += 2
                continue
        result.append(line)
        i += 1
    return "\n".join(result)


def compact_dict_builds(content):
    content = re.sub(
        r'{\s*"(\w+)":\s*(\w+),\s*"(\w+)":\s*(\w+)\s*}', r'{"\1": \2, "\3": \4}', content
    )
    return content


def process_file(filepath):
    with open(filepath) as f:
        content = f.read()

    original_lines = content.count("\n")
    content = compact_conditionals(content)
    content = inline_simple_vars(content)
    content = compact_dict_builds(content)

    with open(filepath, "w") as f:
        f.write(content)

    new_lines = content.count("\n")
    return original_lines, new_lines


def main():
    repo_root = Path(__file__).parent.parent
    exclude = {"__pycache__", ".git", "venv", ".nix-profile", "tests", "scripts"}

    total_before = total_after = 0
    for py_file in repo_root.rglob("*.py"):
        if any(e in py_file.parts for e in exclude):
            continue
        before, after = process_file(py_file)
        total_before += before
        total_after += after
        if before - after > 0:
            print(f"⚡ {py_file.relative_to(repo_root)}: {before} → {after} (-{before - after})")

    print(f"\n📊 Total: {total_before} → {total_after} ({total_before - total_after} lines saved)")


if __name__ == "__main__":
    main()
