#!/usr/bin/env python3
"""Quick script to test if Sentry is configured correctly."""

import os
import sys

print("🔍 Sentry Configuration Check")
print("=" * 50)

# Check environment variables
sentry_dsn = os.environ.get("SENTRY_DSN")
environment = os.environ.get("ENVIRONMENT", "development")

print("\n1. Environment Variables:")
print(f"   SENTRY_DSN: {'✅ Set' if sentry_dsn else '❌ Not set'}")
if sentry_dsn:
    # Mask the DSN for security
    masked_dsn = sentry_dsn[:30] + "..." if len(sentry_dsn) > 30 else sentry_dsn
    print(f"   DSN (masked): {masked_dsn}")
print(f"   ENVIRONMENT: {environment}")

# Check if sentry-sdk is installed
print("\n2. Sentry SDK Installation:")
try:
    import sentry_sdk

    print(f"   ✅ sentry-sdk is installed (version: {sentry_sdk.VERSION})")
except ImportError:
    print("   ❌ sentry-sdk is NOT installed")
    print("   Run: pip install 'sentry-sdk[fastapi]'")
    sys.exit(1)

# Check if Sentry would initialize
print("\n3. Sentry Initialization Check:")
if sentry_dsn:
    print("   ✅ DSN is set - Sentry WILL initialize")
    print(f"   Environment: {environment}")

    # Try to initialize (without actually sending events)
    try:
        from core.monitoring.sentry import init_sentry

        init_sentry()
        print("   ✅ Sentry initialized successfully!")
    except Exception as e:
        print(f"   ❌ Error initializing Sentry: {e}")
else:
    print("   ⚠️  DSN not set - Sentry will NOT initialize")
    print("   Add SENTRY_DSN to your .env file")

print("\n" + "=" * 50)
print("Done!")
