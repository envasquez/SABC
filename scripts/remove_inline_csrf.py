#!/usr/bin/env python3
"""
Remove inline getCsrfToken() implementations and use the centralized version from utils.js
"""

import re
from pathlib import Path

files_to_fix = [
    "templates/admin/users.html",
    "templates/admin/news.html",
    "templates/admin/users/merge.html",
    "templates/tournament_results.html",
    "templates/polls.html",
]

# Pattern to match inline CSRF token retrieval
inline_csrf_pattern = re.compile(
    r"//\s*Get CSRF token from cookie\s*\n\s*const csrfToken = document\.cookie\s*\n"
    r"\s*\.split\(['\"][;]\s*['\"],?\s*\)\s*\n"
    r"\s*\.find\(row => row\.startsWith\(['\"]csrf_token=['\"],?\s*\)\)\s*\n"
    r"\s*\?\.split\(['\"]=['\"],?\s*\)\[1\];",
    re.MULTILINE,
)

# Simpler pattern
simpler_pattern = re.compile(
    r"const csrfToken = document\.cookie\s*"
    r"\.split\(['\"][;]\s*['\"],?\s*\)\s*"
    r"\.find\(row => row\.startsWith\(['\"]csrf_token=['\"],?\s*\)\)\s*"
    r"\?\.split\(['\"]=['\"],?\s*\)\[1\];",
    re.DOTALL,
)

replacement = "const csrfToken = getCsrfToken();"

total_replacements = 0

for file_path_str in files_to_fix:
    file_path = Path(file_path_str)

    if not file_path.exists():
        print(f"⚠️  {file_path} not found, skipping")
        continue

    content = file_path.read_text()
    original_content = content

    # Try pattern with comment
    content = inline_csrf_pattern.sub(replacement, content)

    # Try simpler pattern (without comment)
    content = simpler_pattern.sub(replacement, content)

    if content != original_content:
        count = original_content.count("document.cookie") - content.count("document.cookie")
        file_path.write_text(content)
        total_replacements += count
        print(f"✓ {file_path.name}: Replaced {count} inline CSRF implementation(s)")

print(f"\n✅ Complete! Removed {total_replacements} inline getCsrfToken() implementations")
print("   All files now use getCsrfToken() from utils.js")
