#!/usr/bin/env python3
"""
Refactor polls.html to use data attributes and PollVotingHandler class
"""

import re


def refactor_polls_html(file_path):
    """Refactor polls.html to use data attributes instead of generated JS"""

    with open(file_path, "r") as f:
        content = f.read()

    original_length = len(content.split("\n"))

    # Step 1: Add data attributes to lake select elements
    # Pattern: <select id="lake_select_admin_own_{{ poll.id }}" ... onchange="updateRampsAdminOwn{{ poll.id }}()">

    # Admin own vote - lake select
    content = re.sub(
        r'(<select id="lake_select_admin_own_{{ poll\.id }}"[^>]*?)onchange="updateRampsAdminOwn{{ poll\.id }}\(\)"',
        r'\1data-poll-id="{{ poll.id }}" data-context="admin_own" data-poll-lake="true"',
        content,
    )

    # Admin proxy vote - lake select
    content = re.sub(
        r'(<select id="admin_lake_select_{{ poll\.id }}"[^>]*?)onchange="updateAdminRamps{{ poll\.id }}\(\)"',
        r'\1data-poll-id="{{ poll.id }}" data-context="admin_proxy" data-poll-lake="true"',
        content,
    )

    # Non-admin vote - lake select
    content = re.sub(
        r'(<select id="lake_select_nonadmin_{{ poll\.id }}"[^>]*?)onchange="updateRampsNonAdmin{{ poll\.id }}\(\)"',
        r'\1data-poll-id="{{ poll.id }}" data-context="nonadmin" data-poll-lake="true"',
        content,
    )

    # Step 2: Add data attributes to forms and remove onsubmit handlers

    # Admin own vote form
    content = re.sub(
        r'(<form method="POST" action="/polls/{{ poll\.id }}/vote"[^>]*?)onsubmit="return validateVoteAdminOwn{{ poll\.id }}\(\)"',
        r'\1data-poll-vote="true" data-poll-id="{{ poll.id }}" data-poll-type="{{ poll.poll_type }}" data-context="admin_own"',
        content,
    )

    # Admin proxy vote form
    content = re.sub(
        r'(<form method="POST" action="/polls/{{ poll\.id }}/vote_for"[^>]*?)onsubmit="return validateProxyVote{{ poll\.id }}\(\)"',
        r'\1data-poll-vote="true" data-poll-id="{{ poll.id }}" data-poll-type="{{ poll.poll_type }}" data-context="admin_proxy"',
        content,
    )

    # Non-admin vote form
    content = re.sub(
        r'(<form method="POST" action="/polls/{{ poll\.id }}/vote"[^>]*?)onsubmit="return validateVoteNonAdmin{{ poll\.id }}\(\)"',
        r'\1data-poll-vote="true" data-poll-id="{{ poll.id }}" data-poll-type="{{ poll.poll_type }}" data-context="nonadmin"',
        content,
    )

    # Step 3: Remove the entire generated JavaScript block (lines with window.updateRamps*, window.validateVote*)
    # This is between {% for poll in polls %} (around line 937) and {% endif %} (around line 1221)

    # Remove the JavaScript generation loop
    pattern = re.compile(
        r"{% for poll in polls %}\s*"
        r"{% if poll\.poll_type == \'tournament_location\' %}\s*"
        r"// Admin own vote functions.*?"
        r"{% endif %}\s*"
        r"{% endfor %}",
        re.DOTALL,
    )

    content = pattern.sub("", content)

    new_length = len(content.split("\n"))

    with open(file_path, "w") as f:
        f.write(content)

    print(f"✅ Refactored {file_path}")
    print(f"   Original: {original_length} lines")
    print(f"   New: {new_length} lines")
    print(f"   Saved: {original_length - new_length} lines")


if __name__ == "__main__":
    refactor_polls_html("templates/polls.html")
