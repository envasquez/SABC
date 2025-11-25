#!/usr/bin/env python3
"""
Replace manual CSRF token implementations with csrf_token macro
"""

from pathlib import Path

files_to_fix = [
    "templates/admin/create_poll.html",
    "templates/admin/edit_poll.html",
    "templates/admin/edit_tournament_poll.html",
    "templates/admin/lakes.html",
    "templates/admin/enter_results.html",
]

manual_csrf = (
    '<input type="hidden" name="csrf_token" value="{{ request.cookies.get(\'csrf_token\') }}">'
)
macro_csrf = "{{ csrf_token(request) }}"

total_replacements = 0

for file_path_str in files_to_fix:
    file_path = Path(file_path_str)

    if not file_path.exists():
        print(f"⚠️  {file_path} not found, skipping")
        continue

    content = file_path.read_text()

    # Update import statement to include csrf_token
    if (
        "from 'macros.html' import" in content
        and "csrf_token" not in content.split("from 'macros.html' import")[1].split("\n")[0]
    ):
        # Add csrf_token to existing import
        import_line_start = content.find("{% from 'macros.html' import")
        import_line_end = content.find("%}", import_line_start) + 2

        import_line = content[import_line_start:import_line_end]

        # Extract existing imports
        imports_str = import_line.split("import")[1].strip().replace("%}", "").strip()

        # Add csrf_token
        new_imports = imports_str + ", csrf_token"
        new_import_line = f"{{% from 'macros.html' import {new_imports} %}}"

        content = content[:import_line_start] + new_import_line + content[import_line_end:]
        print(f"✓ Updated imports in {file_path.name}")

    # Replace manual CSRF tokens
    count = content.count(manual_csrf)
    if count > 0:
        content = content.replace(manual_csrf, macro_csrf)
        file_path.write_text(content)
        total_replacements += count
        print(f"  → Replaced {count} manual CSRF token(s)")

print(
    f"\n✅ Complete! Replaced {total_replacements} manual CSRF tokens across {len(files_to_fix)} files"
)
