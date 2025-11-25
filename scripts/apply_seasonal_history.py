#!/usr/bin/env python3
"""
Apply seasonal_history_card macro to replace 3 duplicate blocks in polls.html
"""

import re
from pathlib import Path

polls_path = Path("templates/polls.html")
content = polls_path.read_text()

# The detailed seasonal history card appears 3 times
# Each block is ~70 lines starting with the detailed card structure

# Pattern 1: Active polls section (around line 229-298)
pattern1 = re.compile(
    r"<!-- Seasonal Tournament History for active tournament polls -->.*?"
    r"{% if poll\.poll_type == \'tournament_location\' and poll\.seasonal_history and poll\.seasonal_history\|length > 0 %}.*?"
    r'<div class="mt-4">.*?'
    r'<div class="card border-info">.*?'
    r'<div class="card-header bg-info text-white py-2">.*?'
    r'<h6 class="mb-0">.*?'
    r'<i class="bi bi-calendar3 me-1"></i>.*?'
    r"\{\{ poll\.seasonal_history\[0\]\.month_name \}\} Tournament History.*?"
    r"</h6>.*?"
    r"</div>.*?"
    r"</div>.*?"
    r'<div class="card-body p-3">.*?'
    r'<div class="row g-2">.*?'
    r"{% for hist in poll\.seasonal_history %}.*?"
    r"{% endfor %}.*?"
    r"</div>.*?"
    r"</div>.*?"
    r"</div>.*?"
    r"</div>.*?"
    r"{% endif %}",
    re.DOTALL,
)

# Simpler approach: find the large blocks by searching for unique markers
# Looking for the pattern starting with "Seasonal Tournament History" comment

# Let's use a more targeted approach - find each occurrence separately

# First occurrence - around line 229
first_block_start = content.find("<!-- Seasonal Tournament History for active tournament polls -->")
if first_block_start > 0:
    # Find the end of this block (next closing endif for seasonal_history)
    search_start = first_block_start
    # Look for the pattern of the full card
    next_section = content.find(
        "{% endif %} <!-- Close else for user_has_voted (admin tab) -->", search_start
    )
    if next_section > 0:
        # The seasonal history block ends just before this
        # Find the endif that closes the seasonal_history conditional
        temp = content[search_start:next_section]
        endif_pos = temp.rfind("{% endif %}")
        if endif_pos > 0:
            first_block_end = search_start + endif_pos + len("{% endif %}")
            first_block = content[first_block_start:first_block_end]

            # Replace with macro call
            replacement1 = """<!-- Seasonal Tournament History for active tournament polls -->
                            {% if poll.poll_type == 'tournament_location' and poll.seasonal_history and poll.seasonal_history|length > 0 %}
                            <div class="mt-4">
                                {{ seasonal_history_card(poll.seasonal_history) }}
                            </div>
                            {% endif %}"""

            content = content[:first_block_start] + replacement1 + content[first_block_end:]

# Second occurrence - upcoming polls section
second_block_start = content.find(
    "<!-- Seasonal Tournament History for upcoming tournament polls -->"
)
if second_block_start > 0:
    search_start = second_block_start
    # Find the next major section
    next_section = content.find(
        "{% endif %} <!-- Close else for user_has_voted (upcoming tab) -->", search_start
    )
    if next_section > 0:
        temp = content[search_start:next_section]
        endif_pos = temp.rfind("{% endif %}")
        if endif_pos > 0:
            second_block_end = search_start + endif_pos + len("{% endif %}")

            replacement2 = """<!-- Seasonal Tournament History for upcoming tournament polls -->
                            {% if poll.poll_type == 'tournament_location' and poll.seasonal_history and poll.seasonal_history|length > 0 %}
                            <div class="mt-4">
                                {{ seasonal_history_card(poll.seasonal_history) }}
                            </div>
                            {% endif %}"""

            content = content[:second_block_start] + replacement2 + content[second_block_end:]

# Third occurrence - results section
third_block_start = content.find(
    "<!-- Seasonal Tournament History -->", second_block_start if second_block_start > 0 else 0
)
if third_block_start > 0:
    search_start = third_block_start
    # This one is inside a results tab
    # Find the endif that belongs to this seasonal_history check
    temp_content = content[search_start:]
    # Count the card divs to find where this block ends
    # Look for the next major section marker
    next_marker = temp_content.find("</div> <!-- Close results card -->")
    if next_marker > 0:
        section_to_search = temp_content[:next_marker]
        # Find the seasonal history endif
        seasonal_endif = section_to_search.rfind("{% endif %}")
        if seasonal_endif > 0:
            third_block_end = search_start + seasonal_endif + len("{% endif %}")

            replacement3 = """<!-- Seasonal Tournament History -->
                                    {% if poll.seasonal_history and poll.seasonal_history|length > 0 %}
                                    <div class="mt-4">
                                        {{ seasonal_history_card(poll.seasonal_history) }}
                                    </div>
                                    {% endif %}"""

            content = content[:third_block_start] + replacement3 + content[third_block_end:]

polls_path.write_text(content)
print("✅ Applied seasonal_history_card macro to 3 locations in polls.html")
print("   Checking line count...")

# Count lines
new_lines = len(content.splitlines())
print(f"   New line count: {new_lines}")
