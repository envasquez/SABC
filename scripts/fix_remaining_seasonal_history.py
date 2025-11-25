#!/usr/bin/env python3
"""
Replace remaining 3 detailed seasonal history cards with macro calls in polls.html
"""

import re
from pathlib import Path

polls_path = Path("templates/polls.html")
content = polls_path.read_text()

# Pattern to match the detailed seasonal history card blocks
# These start with comment and detailed card structure
pattern = re.compile(
    r"<!-- Seasonal Tournament History.*?-->\s*"
    r"{% if poll\.(?:poll_type == 'tournament_location' and )?seasonal_history and poll\.seasonal_history\|length > 0 %}\s*"
    r"<div class=\"mt-4\">\s*"
    r"<div class=\"card border-info\">.*?"
    r"{% for hist in poll\.seasonal_history %}.*?"
    r"{% endfor %}\s*"
    r"</div>\s*"
    r"</div>\s*"
    r"</div>\s*"
    r"</div>\s*"
    r"{% endif %}",
    re.DOTALL,
)

# Replacement patterns for each context
# Active polls
replacement_active = """<!-- Seasonal Tournament History for active tournament polls -->
                            {% if poll.poll_type == 'tournament_location' and poll.seasonal_history and poll.seasonal_history|length > 0 %}
                            <div class="mt-4">
                                {{ seasonal_history_card(poll.seasonal_history) }}
                            </div>
                            {% endif %}"""

# Upcoming polls
replacement_upcoming = """<!-- Seasonal Tournament History for upcoming tournament polls -->
                            {% if poll.poll_type == 'tournament_location' and poll.seasonal_history and poll.seasonal_history|length > 0 %}
                            <div class="mt-4">
                                {{ seasonal_history_card(poll.seasonal_history) }}
                            </div>
                            {% endif %}"""

# Results/closed polls
replacement_results = """<!-- Seasonal Tournament History -->
                                    {% if poll.seasonal_history and poll.seasonal_history|length > 0 %}
                                    <div class="mt-4">
                                        {{ seasonal_history_card(poll.seasonal_history) }}
                                    </div>
                                    {% endif %}"""

# Find and replace all matches
matches = list(pattern.finditer(content))
print(f"Found {len(matches)} seasonal history card blocks to replace")

# Replace from end to start to preserve positions
for i, match in enumerate(reversed(matches)):
    match_num = len(matches) - i
    start, end = match.span()

    # Determine which replacement based on the comment
    if "active tournament polls" in match.group():
        replacement = replacement_active
        context = "active"
    elif "upcoming tournament polls" in match.group():
        replacement = replacement_upcoming
        context = "upcoming"
    else:
        replacement = replacement_results
        context = "results"

    print(f"  Replacing match {match_num} ({context}) at lines ~{content[:start].count(chr(10))}")
    content = content[:start] + replacement + content[end:]

polls_path.write_text(content)

# Check results
new_lines = len(content.splitlines())
remaining_detailed = content.count("hist.num_anglers")

print("\n✅ Replacement complete!")
print(f"   New line count: {new_lines}")
print(f"   Remaining detailed cards: {remaining_detailed} (should be 0)")

if remaining_detailed > 0:
    print(f"   ⚠️  Warning: Still found {remaining_detailed} detailed cards")
