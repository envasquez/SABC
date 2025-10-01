import sys
from pathlib import Path

MAX_LINES = 100
EXCLUDE_DIRS = {"__pycache__", ".git", "venv", ".nix-profile", "tests"}


def check_file_length(filepath: Path) -> tuple[bool, int]:
    with open(filepath) as f:
        lines = len(f.readlines())
    return lines <= MAX_LINES, lines


def main():
    violations = []
    repo_root = Path(__file__).parent.parent

    for py_file in repo_root.rglob("*.py"):
        if any(excluded in py_file.parts for excluded in EXCLUDE_DIRS):
            continue

        is_valid, line_count = check_file_length(py_file)
        if not is_valid:
            violations.append((py_file, line_count))

    if violations:
        print(f"❌ {len(violations)} files exceed {MAX_LINES} line limit:\n")
        for filepath, lines in sorted(violations, key=lambda x: -x[1]):
            rel_path = filepath.relative_to(repo_root)
            excess = lines - MAX_LINES
            print(f"  {lines:4d} lines (+{excess:3d} over): {rel_path}")
        print("\n💡 Hint: Split large files into smaller modules")
        print("   Each file should focus on a single responsibility")
        sys.exit(1)
    else:
        print(f"✅ All Python files are under {MAX_LINES} lines!")
        sys.exit(0)


if __name__ == "__main__":
    main()
