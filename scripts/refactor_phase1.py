#!/usr/bin/env python3
"""
Phase 1 refactoring script: Replace time dropdown duplications with macro calls
"""

import re
from pathlib import Path

# Read polls.html
polls_html_path = Path("templates/polls.html")
content = polls_html_path.read_text()

# Pattern to match time option blocks (from 05:00 to 20:00)
time_options_pattern = r'<option value="">(?:Start|End)\.\.\.< /option>\s*<option value="05:00">5:00 AM</option>.*?<option value="20:00">8:00 PM</option>'

# First, update the import statement
content = content.replace(
    "{% from 'macros.html' import alert, badge, csrf_token, delete_modal %}",
    "{% from 'macros.html' import alert, badge, csrf_token, delete_modal, time_select_options, seasonal_history_card %}",
)

# Find all time dropdown blocks and replace with macro
# This is complex because we need to handle multiline and preserve context
# Let's do a simpler approach: replace the entire option list with macro call

# Pattern for start time dropdowns
start_time_pattern = re.compile(
    r'<option value="">Start\.\.\.</option>\s*'
    r'<option value="05:00">5:00 AM</option>.*?'
    r'<option value="20:00">8:00 PM</option>',
    re.DOTALL,
)

# Pattern for end time dropdowns
end_time_pattern = re.compile(
    r'<option value="">End\.\.\.</option>\s*'
    r'<option value="05:00">5:00 AM</option>.*?'
    r'<option value="20:00">8:00 PM</option>',
    re.DOTALL,
)

# Replace start time dropdowns
content = start_time_pattern.sub(
    '<option value="">Start...</option>\n{{ time_select_options(5, 20, 30) }}', content
)

# Replace end time dropdowns
content = end_time_pattern.sub(
    '<option value="">End...</option>\n{{ time_select_options(5, 20, 30, "15:00") }}', content
)

# Write the updated content
polls_html_path.write_text(content)

print(f"✅ Updated {polls_html_path}")
print("   - Added time_select_options and seasonal_history_card to imports")
print("   - Replaced time dropdown duplications with macro calls")
