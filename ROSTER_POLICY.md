# SABC Roster Policy

## Guest Policy

The SABC roster correctly displays "No guest members at this time" because per the official CLAUDE.md requirements:

> **NO Guest Angler entries** - convert to actual names or remove

This is not a bug - it's the intended behavior.

## Current Status

- **Total Members**: 56 active members with real names
- **Total Guests**: 0 (as required by policy)
- **Placeholder Entries**: 1 entry ("James Guest") flagged for cleanup

## Data Cleanup Required

The following entry requires attention per the guest policy:

- **James Guest** (inactive member with 1 tournament result from 2025-03-23)
  - Should be converted to real name using reference site validation
  - Or removed if no matching real person exists

## Reference Site Validation

This cleanup should be performed as part of Issue #133 (Missing Critical: Reference Site Validation System) which will:

1. Validate all member data against http://167.71.20.3
2. Identify real names for any placeholder entries
3. Ensure compliance with "NO Guest Angler entries" policy

## Roster Display Logic

The roster template correctly:
- Shows all members with `member = 1` in the "Anglers" section  
- Looks for guests with `member = 0` in the "Guests" section
- Displays "No guest members at this time" when no `member = 0` entries exist
- This is the expected and correct behavior per SABC policy