# Account Merge Tool

## Overview

The Account Merge Tool allows administrators to consolidate duplicate user accounts into a single account. This is useful when users accidentally create multiple accounts with the same name but different email addresses.

## When to Use This Tool

Use the account merge tool when:

- A user created a new account with a different email address
- The old account has historical data (tournament results, votes, etc.) that needs to be preserved
- You want to consolidate all data into the active account

**⚠️ Important:** This operation moves data from one account to another. It cannot be easily undone. Always review the preview carefully before proceeding.

## Step-by-Step Guide

### 1. Access the Merge Interface

1. Log in as an admin
2. Navigate to **Admin → Manage Anglers**
3. Click the **"Merge Accounts"** button (yellow button, top right)

### 2. Select Accounts

**Source Account (Old)**
- This is the account you want to merge FROM
- All data will be moved OUT of this account
- Displayed in red/danger styling
- Select from the dropdown: shows name, email, and ID

**Target Account (New)**
- This is the account you want to merge TO
- All data will be moved INTO this account
- Displayed in green/success styling
- Select from the dropdown: shows name, email, and ID

**⚠️ Important:** Make sure you select the correct direction! Data flows FROM source TO target.

### 3. Review the Preview

Once both accounts are selected, the preview section automatically loads and shows:

#### Data to be Migrated

- **Tournament Results:** Individual tournament results count
- **Team Results:** Team tournament results count
- **Poll Votes:** Individual poll votes count
- **Officer Positions:** Officer position assignments count
- **Polls Created:** Polls created by this user
- **News Articles:** News articles authored by this user
- **Tournaments Created:** Tournaments created by this user
- **Proxy Votes Cast:** Votes cast on behalf of others (admin feature)

#### Duplicate Vote Warning

If both accounts have voted on the same poll(s), you'll see a warning:

```
⚠️ Duplicate Poll Votes Detected
Both accounts have voted on the following polls. The source account's votes will be deleted:
- [Poll Title]
- [Poll Title]
```

This is expected behavior to maintain database integrity (each user can only vote once per poll).

### 4. Execute the Merge

1. **Review the preview carefully** - verify counts are what you expect
2. **Check the confirmation box**: "I understand this action cannot be undone and I have reviewed the preview above"
3. **Click "Execute Merge"** button (red/danger button)

The system will:
- Move all tournament results to the target account
- Move all team results to the target account
- Move all poll votes to the target account (removing duplicates)
- Move all officer positions to the target account
- Update all created content to show target account as creator
- Delete password reset tokens for the source account
- Log the entire operation for audit purposes

### 5. Post-Merge Actions

After a successful merge, you'll see:

- **Success summary** with detailed counts of migrated data
- **Source account status** - account still exists but is now empty
- **Target account status** - now contains all consolidated data

#### Optional: Delete the Old Account

The source account remains in the system for audit purposes. You can optionally delete it:

1. Review the migration summary to ensure everything migrated correctly
2. Click **"Delete Old Account"** button
3. Confirm the deletion when prompted

**⚠️ Warning:** Deleting the account is permanent and cannot be undone.

## Technical Details

### Database Tables Affected

The merge operation updates the following tables:

#### Primary Data (CASCADE delete behavior)
- `results.angler_id` - Tournament results
- `team_results.angler1_id` - Team tournament participant 1
- `team_results.angler2_id` - Team tournament participant 2
- `poll_votes.angler_id` - Poll votes
- `officer_positions.angler_id` - Officer positions

#### Nullable References (SET NULL behavior)
- `poll_votes.cast_by_admin_id` - Proxy votes cast by admin
- `polls.created_by` - Poll creator
- `news.author_id` - News article author
- `tournaments.created_by` - Tournament creator

#### Deleted Records
- `password_reset_tokens.user_id` - Password reset tokens (cleaned up)

### Transaction Safety

The merge operation runs within a database transaction:

- **Success:** All changes are committed together
- **Failure:** All changes are rolled back automatically
- **Error handling:** User-friendly error messages are displayed
- **Audit logging:** All operations are logged with admin ID and timestamp

### Duplicate Vote Handling

The unique constraint `uq_poll_vote_angler` ensures each angler can only vote once per poll.

When both accounts have voted on the same poll:
1. The system detects the duplicate
2. Shows a warning in the preview
3. Deletes the source account's vote
4. Keeps the target account's vote
5. Logs the deletion

This prevents constraint violations and maintains data integrity.

## Troubleshooting

### "Source and target accounts must be different"

**Problem:** You selected the same account for both source and target.

**Solution:** Select two different accounts. Data must flow from one account to another.

### "Failed to load preview: The string did not match the expected pattern"

**Problem:** JavaScript/CSRF error (should be fixed in latest version).

**Solution:**
1. Hard refresh the page (Cmd+Shift+R or Ctrl+Shift+F5)
2. Try selecting the accounts again
3. Check browser console for errors

### "Merge failed: Database integrity error"

**Problem:** Database constraint violation.

**Solution:**
1. Check the error message for details
2. All changes were rolled back automatically
3. Report the error to a developer if it persists

### "Cannot delete account: still has X records"

**Problem:** Trying to delete an account that wasn't fully merged.

**Solution:**
1. Verify the merge completed successfully
2. Check database manually for remaining data
3. Only delete accounts that show 0 records in all categories

## Security Considerations

### Admin-Only Access

- All merge routes require admin authentication
- Regular users cannot access the merge interface
- Admin status is verified on every request

### CSRF Protection

- All forms include CSRF tokens
- AJAX requests include CSRF headers
- Invalid tokens result in 403 Forbidden errors

### Audit Logging

Every merge operation logs:
- Timestamp of operation
- Admin user ID who performed the merge
- Source account ID
- Target account ID
- Counts of all migrated data
- Any errors that occurred

Logs are stored in the application log file and can be reviewed for audit purposes.

### Data Integrity

- Foreign key constraints prevent orphaned records
- Unique constraints prevent duplicate votes
- Transaction rollback prevents partial merges
- Validation checks prevent invalid merges

## Best Practices

### Before Merging

1. **Verify account ownership** - Confirm with the user which account they want to keep
2. **Check data distribution** - Review which account has more historical data
3. **Note important details** - Record both account IDs and emails for reference
4. **Screenshot the preview** - Save a copy of the migration summary
5. **Check for duplicates** - Review the duplicate vote warning if present

### During Merge

1. **Read all warnings** - Pay attention to duplicate vote warnings
2. **Verify the direction** - Double-check source→target direction
3. **Review all counts** - Ensure numbers match expectations
4. **Don't rush** - Take time to verify before clicking "Execute"

### After Merge

1. **Verify success** - Check the success summary matches preview
2. **Test login** - Have user verify they can log in with target account
3. **Check data** - Spot-check a few tournament results to verify migration
4. **Document** - Note the merge in your admin log or records
5. **Delay deletion** - Keep source account for a few days before deleting

### When Things Go Wrong

1. **Don't panic** - Transaction rollback prevents partial merges
2. **Read error message** - Error messages provide details
3. **Check logs** - Review application logs for full error details
4. **Document issue** - Note what happened for future reference
5. **Ask for help** - Contact a developer if error persists

## Frequently Asked Questions

### Can I undo a merge?

No, the merge cannot be easily undone. You would need to manually move data back, which is complex and error-prone. Always review carefully before executing.

### What happens to the old account after merge?

The source account remains in the system but has no data. You can optionally delete it, but it's kept by default for audit purposes.

### Can I merge more than two accounts?

The tool merges two accounts at a time. To consolidate three accounts:
1. Merge account A → B
2. Merge account B → C

### What if both accounts have different data?

That's the ideal use case! The merge consolidates all unique data into the target account. Duplicates (like poll votes) are handled automatically.

### Can regular users merge accounts?

No, only administrators can access the merge tool.

### What happens to the user's login credentials?

The target account's email and password remain unchanged. The source account's login credentials are kept with the source account (which will be empty after merge).

### How long does a merge take?

Most merges complete in under 1 second. Large accounts (100+ tournament results) may take 2-3 seconds.

### Can I merge admin accounts?

Yes, but be careful! If you merge away an admin account, make sure the target account has admin privileges.

## Summary

The Account Merge Tool is a powerful admin feature for consolidating duplicate user accounts. With proper care and attention to the preview, it safely migrates all historical data while maintaining database integrity.

**Key Points:**
- ✅ Admin-only access
- ✅ Preview before execution
- ✅ Transaction safety with rollback
- ✅ Automatic duplicate handling
- ✅ Comprehensive audit logging
- ⚠️ Cannot be easily undone
- ⚠️ Review carefully before executing

For questions or issues, consult the application logs or contact a developer.
