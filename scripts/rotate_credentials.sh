#!/bin/bash
# SABC Credential Rotation Script
# Guides you through rotating all security-critical credentials

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${RED}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║                                                                ║${NC}"
echo -e "${RED}║         🚨 SABC CREDENTIAL ROTATION WIZARD 🚨                  ║${NC}"
echo -e "${RED}║                                                                ║${NC}"
echo -e "${RED}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}This script will guide you through rotating all security credentials.${NC}"
echo -e "${YELLOW}Have access to Gmail, database admin, and deployment platform ready.${NC}"
echo ""

read -p "Continue with credential rotation? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Credential rotation cancelled."
    exit 0
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 1: Generate New SECRET_KEY${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

NEW_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo -e "${GREEN}Generated new SECRET_KEY (64 characters):${NC}"
echo "$NEW_SECRET_KEY"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: Changing SECRET_KEY will:${NC}"
echo -e "${YELLOW}   - Invalidate ALL existing user sessions (users must re-login)${NC}"
echo -e "${YELLOW}   - Invalidate ALL password reset tokens${NC}"
echo -e "${YELLOW}   - Invalidate ALL CSRF tokens${NC}"
echo ""
read -p "Copy this SECRET_KEY to your .env file and press Enter to continue..."

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 2: Rotate Gmail App Password${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Current exposed password: mjpu bxfh yglw geqo"
echo ""
echo -e "${RED}IMMEDIATELY revoke this password:${NC}"
echo "1. Go to: https://myaccount.google.com/apppasswords"
echo "2. Sign in to southasutinbassclub@gmail.com (or your SMTP account)"
echo "3. Find 'SABC FastAPI' app password"
echo "4. Click 'Delete' or 'Revoke'"
echo ""
read -p "Press Enter after revoking the old password..."

echo ""
echo -e "${GREEN}Now generate a new App Password:${NC}"
echo "1. Still at: https://myaccount.google.com/apppasswords"
echo "2. Click 'Select app' → 'Other (custom name)'"
echo "3. Enter name: 'SABC FastAPI Production $(date +%Y-%m-%d)'"
echo "4. Click 'Generate'"
echo "5. Copy the 16-character password (format: xxxx xxxx xxxx xxxx)"
echo ""
read -p "Enter new SMTP_PASSWORD: " NEW_SMTP_PASSWORD
echo ""
echo -e "${YELLOW}Update your .env file with:${NC}"
echo "SMTP_PASSWORD=$NEW_SMTP_PASSWORD"
echo ""
read -p "Press Enter after updating .env file..."

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 3: Database Password Review${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
read -p "Was the database password potentially exposed? (yes/no): " DB_EXPOSED

if [ "$DB_EXPOSED" == "yes" ]; then
    echo ""
    echo -e "${YELLOW}Database password rotation required.${NC}"
    echo ""
    echo -e "${RED}For PostgreSQL:${NC}"
    echo "  psql -U postgres"
    echo "  ALTER USER your_db_user WITH PASSWORD 'new_secure_password';"
    echo "  \\q"
    echo ""
    echo -e "${YELLOW}Generate secure password (20+ characters):${NC}"
    DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
    echo "$DB_PASSWORD"
    echo ""
    echo -e "${YELLOW}Update DATABASE_URL in .env:${NC}"
    echo "DATABASE_URL=postgresql://user:$DB_PASSWORD@localhost:5432/sabc"
    echo ""
    read -p "Press Enter after updating database password..."
else
    echo -e "${GREEN}✓ Database password not exposed - no action needed${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 4: Update Production Environment Variables${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Update environment variables in your hosting platform:${NC}"
echo ""
echo -e "${GREEN}Digital Ocean App Platform:${NC}"
echo "1. Go to your app → Settings → App-Level Environment Variables"
echo "2. Update SECRET_KEY to: $NEW_SECRET_KEY"
echo "3. Update SMTP_PASSWORD to: $NEW_SMTP_PASSWORD"
if [ "$DB_EXPOSED" == "yes" ]; then
    echo "4. Update DATABASE_URL with new database password"
fi
echo ""
echo -e "${GREEN}Other platforms (AWS, Heroku, etc.):${NC}"
echo "Update the same environment variables in your platform's secrets manager"
echo ""
read -p "Press Enter after updating production environment variables..."

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 5: Redeploy Application${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Redeploy to apply new credentials:${NC}"
echo ""
echo "For Digital Ocean:"
echo "  doctl apps create-deployment <app-id>"
echo ""
echo "Or trigger deployment via platform UI/webhook"
echo ""
read -p "Press Enter after redeployment completes..."

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 6: Verify & Test${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Test checklist:${NC}"
echo "[ ] Application starts successfully"
echo "[ ] User login works (test account)"
echo "[ ] Password reset email sends successfully"
echo "[ ] Database connection works"
echo "[ ] All existing sessions invalidated (logout required)"
echo "[ ] Check application logs for errors"
echo ""
read -p "Press Enter after verifying all tests pass..."

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 7: Clean Up & Document${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Final steps:${NC}"
echo "1. Clear this terminal history:"
echo "   history -c"
echo "2. Document rotation in incident log"
echo "3. Update SECURITY.md with rotation date"
echo "4. Notify team members of session invalidation"
echo "5. Monitor logs for 24 hours for anomalies"
echo ""

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║         ✅ CREDENTIAL ROTATION COMPLETE ✅                      ║${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Summary of rotated credentials:${NC}"
echo "  ✓ SECRET_KEY (64 chars)"
echo "  ✓ SMTP_PASSWORD (Gmail App Password)"
if [ "$DB_EXPOSED" == "yes" ]; then
    echo "  ✓ Database password"
fi
echo ""
echo -e "${YELLOW}Next security review: $(date -v+3m +%Y-%m-%d)${NC}"
echo ""
echo -e "${RED}⚠️  REMINDER: Never commit .env files to git!${NC}"
echo ""
