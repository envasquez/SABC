# 🚨 URGENT: Credential Rotation Required

## Quick Action Checklist (Complete within 24 hours)

### ✅ Already Completed (Automated)
- [x] Enhanced `.gitignore` to prevent future leaks
- [x] Created security documentation
- [x] Verified `.env` never committed to git
- [x] Added pre-commit hooks for secret detection
- [x] Created rotation automation tools

### ⚠️ MANUAL ACTIONS REQUIRED

#### 1. Revoke Exposed Gmail Password (5 minutes)
```
URL: https://myaccount.google.com/apppasswords
Account: Your SMTP email account
Action: Delete/Revoke password containing: mjpu bxfh yglw geqo
```

#### 2. Generate New Gmail Password (2 minutes)
```
URL: https://myaccount.google.com/apppasswords
Action: Create new app password
Name: SABC FastAPI Production 2025-10-07
Copy: 16-character password (format: xxxx xxxx xxxx xxxx)
```

#### 3. Generate New SECRET_KEY (30 seconds)
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
Copy the 64-character output

#### 4. Update Local .env File (2 minutes)
Create/edit `.env` in project root:
```bash
SECRET_KEY=<paste-64-char-key-from-step-3>
SMTP_PASSWORD=<paste-16-char-password-from-step-2>
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/sabc
```

#### 5. Update Production Environment (5 minutes)

**Digital Ocean:**
1. Go to: Apps → Your App → Settings → Environment Variables
2. Update `SECRET_KEY` with new value
3. Update `SMTP_PASSWORD` with new value
4. Click "Save"

**Other Platforms:**
Update environment variables in your hosting platform's UI/CLI

#### 6. Redeploy Application (5 minutes)
```bash
# Digital Ocean CLI
doctl apps create-deployment <app-id>

# Or use platform UI to trigger deployment
```

#### 7. Verify Everything Works (10 minutes)
- [ ] Application starts without errors
- [ ] Can log in with test account
- [ ] Password reset email sends successfully
- [ ] Database queries work
- [ ] Check logs for errors

---

## Automated Wizard (Recommended)

**Run the interactive rotation wizard:**
```bash
cd /Users/env/Development/SABC
./scripts/rotate_credentials.sh
```
This will guide you through all steps above.

---

## Expected Impact

**⚠️ Users will be logged out** - SECRET_KEY rotation invalidates sessions
**📧 Brief email interruption** - During SMTP password rotation
**💾 Database unaffected** - Unless password was compromised

---

## After Rotation

1. **Install pre-commit hooks:**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

2. **Test secret detection:**
   ```bash
   pre-commit run detect-secrets --all-files
   ```

3. **Document completion:**
   Update `CREDENTIAL_ROTATION_SUMMARY.md` with completion date

---

## Need Help?

- **Full Guide**: See [SECURITY.md](SECURITY.md)
- **Detailed Timeline**: See [CREDENTIAL_ROTATION_SUMMARY.md](CREDENTIAL_ROTATION_SUMMARY.md)
- **Environment Setup**: See [.env.example](.env.example)

---

## Timeline Estimate

| Task | Time | Critical? |
|------|------|-----------|
| Revoke old password | 5 min | YES |
| Generate new password | 2 min | YES |
| Generate SECRET_KEY | 30 sec | YES |
| Update .env | 2 min | YES |
| Update production | 5 min | YES |
| Redeploy | 5 min | YES |
| Verify | 10 min | YES |
| **TOTAL** | **~30 min** | **Complete within 24 hours** |

---

🚨 **START NOW** - The exposed Gmail password grants full email access!
