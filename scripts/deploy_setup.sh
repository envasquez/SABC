#!/bin/bash
#
# SABC Deployment Setup Script
# This script initializes the database for deployment
#
# Usage: ./scripts/deploy_setup.sh [--skip-admin] [--year YEAR]
#

set -e  # Exit on error

# Default values
SKIP_ADMIN=false
YEAR=$(date +%Y)
NEXT_YEAR=$((YEAR + 1))

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-admin)
            SKIP_ADMIN=true
            shift
            ;;
        --year)
            YEAR="$2"
            NEXT_YEAR=$((YEAR + 1))
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--skip-admin] [--year YEAR]"
            echo ""
            echo "Options:"
            echo "  --skip-admin  Skip admin user creation (if already exists)"
            echo "  --year YEAR   Specify the year for holidays (default: current year)"
            echo "  --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "=========================================="
echo "  SABC Deployment Database Setup"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "Error: This script must be run from the project root directory"
    exit 1
fi

# Check for required environment variable
if [ -z "$DATABASE_URL" ]; then
    echo "Warning: DATABASE_URL not set"
    echo "Using default: postgresql://postgres:dev123@localhost:5432/sabc"
    export DATABASE_URL="postgresql://postgres:dev123@localhost:5432/sabc"
fi

echo "Database URL: $DATABASE_URL"
echo ""

# Step 1: Initialize database schema
echo "Step 1: Initializing database schema..."
python scripts/init_postgres.py
if [ $? -eq 0 ]; then
    echo "✅ Database schema initialized successfully"
else
    echo "❌ Failed to initialize database schema"
    exit 1
fi
echo ""

# Step 2: Load lakes data
echo "Step 2: Loading lakes data..."
python scripts/load_lakes.py
if [ $? -eq 0 ]; then
    echo "✅ Lakes data loaded successfully"
else
    echo "❌ Failed to load lakes data"
    exit 1
fi
echo ""

# Step 3: Load holidays
echo "Step 3: Loading holidays for years $YEAR and $NEXT_YEAR..."
python scripts/load_holidays.py $YEAR $NEXT_YEAR
if [ $? -eq 0 ]; then
    echo "✅ Holidays loaded successfully"
else
    echo "❌ Failed to load holidays"
    exit 1
fi
echo ""

# Step 4: Create admin user
if [ "$SKIP_ADMIN" = true ]; then
    echo "Step 4: Skipping admin user creation (--skip-admin flag)"
else
    echo "Step 4: Creating admin user..."
    echo "You'll be prompted to enter admin credentials"
    python scripts/bootstrap_admin_postgres.py
    if [ $? -eq 0 ]; then
        echo "✅ Admin user created successfully"
    else
        echo "❌ Failed to create admin user"
        exit 1
    fi
fi
echo ""

echo "=========================================="
echo "  Deployment Setup Complete!"
echo "=========================================="
echo ""
echo "✅ Database schema initialized"
echo "✅ Lakes data loaded"
echo "✅ Holidays loaded for $YEAR and $NEXT_YEAR"
if [ "$SKIP_ADMIN" = false ]; then
    echo "✅ Admin user created"
fi
echo ""
echo "Next steps:"
echo "1. Ensure environment variables are set:"
echo "   - DATABASE_URL (database connection)"
echo "   - SECRET_KEY (session security)"
echo "   - SMTP_* (email configuration for password resets)"
echo ""
echo "2. Start the application:"
echo "   uvicorn app:app --host 0.0.0.0 --port 8000"
echo ""