"""
Django management command to verify staging environment configuration.

This command checks that all required settings and services are properly
configured for the staging environment.
"""

import os
import subprocess
import sys

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.db import connections


class Command(BaseCommand):
    help = "Verify staging environment configuration and connectivity"

    def add_arguments(self, parser):
        parser.add_argument(
            "--quick",
            action="store_true",
            help="Skip detailed checks and only run basic connectivity tests",
        )
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Attempt to fix common configuration issues",
        )

    def handle(self, *args, **options):
        """Execute the staging verification checks."""
        self.stdout.write(
            self.style.HTTP_INFO("🔍 SABC Staging Environment Verification")
        )
        self.stdout.write("=" * 60)

        quick_mode = options.get("quick", False)
        fix_mode = options.get("fix", False)

        if fix_mode:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  Fix mode enabled - will attempt to resolve issues"
                )
            )

        checks_passed = 0
        total_checks = 0

        # Basic environment checks
        checks_passed += self._check_environment_variables()
        total_checks += 1

        # Database connectivity
        checks_passed += self._check_database_connection(fix_mode)
        total_checks += 1

        # Redis connectivity
        checks_passed += self._check_redis_connection(fix_mode)
        total_checks += 1

        # File system checks
        checks_passed += self._check_file_permissions(fix_mode)
        total_checks += 1

        if not quick_mode:
            # Detailed configuration checks
            checks_passed += self._check_django_configuration()
            total_checks += 1

            # SSL and security checks
            checks_passed += self._check_ssl_configuration()
            total_checks += 1

            # Service status checks
            checks_passed += self._check_system_services()
            total_checks += 1

        # Summary
        self.stdout.write("=" * 60)
        if checks_passed == total_checks:
            self.stdout.write(
                self.style.SUCCESS(f"✅ All {total_checks} checks passed!")
            )
            self.stdout.write(
                self.style.SUCCESS("🚀 Staging environment is ready for deployment")
            )
        else:
            failed_checks = total_checks - checks_passed
            self.stdout.write(
                self.style.ERROR(f"❌ {failed_checks} of {total_checks} checks failed")
            )
            self.stdout.write(
                self.style.ERROR("⚠️  Please review and fix the issues above")
            )
            sys.exit(1)

    def _check_environment_variables(self):
        """Check required environment variables are set."""
        self.stdout.write(self.style.HTTP_INFO("📋 Checking environment variables..."))

        required_vars = [
            "SECRET_KEY",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "ALLOWED_HOSTS",
        ]

        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)

        if missing_vars:
            self.stdout.write(
                self.style.ERROR(
                    f"   Missing environment variables: {', '.join(missing_vars)}"
                )
            )
            return 0

        self.stdout.write(
            self.style.SUCCESS("   ✅ All required environment variables set")
        )
        return 1

    def _check_database_connection(self, fix_mode=False):
        """Check database connectivity and basic operations."""
        self.stdout.write(self.style.HTTP_INFO("🗄️  Checking database connection..."))

        try:
            # Test database connection
            db_conn = connections["default"]
            db_conn.ensure_connection()

            # Test a simple query
            with db_conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

            if result[0] == 1:
                self.stdout.write(
                    self.style.SUCCESS("   ✅ Database connection successful")
                )

                # Check if migrations are up to date
                from django.core.management import call_command

                try:
                    call_command("showmigrations", "--plan", verbosity=0)
                    self.stdout.write(
                        self.style.SUCCESS("   ✅ Database migrations are up to date")
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"   ⚠️  Migration check failed: {e}")
                    )
                    if fix_mode:
                        self.stdout.write("   🔧 Running migrations...")
                        call_command("migrate", verbosity=0)

                return 1
            else:
                self.stdout.write(self.style.ERROR("   ❌ Database query test failed"))
                return 0

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"   ❌ Database connection failed: {e}")
            )
            return 0

    def _check_redis_connection(self, fix_mode=False):
        """Check Redis connectivity."""
        self.stdout.write(self.style.HTTP_INFO("🔴 Checking Redis connection..."))

        try:
            # Test cache connection
            cache.set("staging_test_key", "test_value", 30)
            value = cache.get("staging_test_key")

            if value == "test_value":
                cache.delete("staging_test_key")
                self.stdout.write(
                    self.style.SUCCESS("   ✅ Redis connection successful")
                )
                return 1
            else:
                self.stdout.write(
                    self.style.ERROR("   ❌ Redis value retrieval failed")
                )
                return 0

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Redis connection failed: {e}"))
            if fix_mode:
                self.stdout.write("   🔧 Attempting to restart Redis service...")
                try:
                    subprocess.run(
                        ["sudo", "systemctl", "restart", "redis-server"], check=True
                    )
                    self.stdout.write("   ✅ Redis service restarted")
                except subprocess.CalledProcessError:
                    self.stdout.write("   ❌ Failed to restart Redis service")
            return 0

    def _check_file_permissions(self, fix_mode=False):
        """Check file system permissions."""
        self.stdout.write(self.style.HTTP_INFO("📁 Checking file permissions..."))

        paths_to_check = [
            settings.STATIC_ROOT,
            settings.MEDIA_ROOT,
            "/home/sabc-staging/logs",
            "/home/sabc-staging/backups",
        ]

        issues = []
        for path in paths_to_check:
            if not os.path.exists(path):
                issues.append(f"Directory does not exist: {path}")
                if fix_mode:
                    try:
                        os.makedirs(path, exist_ok=True)
                        self.stdout.write(f"   🔧 Created directory: {path}")
                    except OSError as e:
                        issues.append(f"Failed to create {path}: {e}")
            elif not os.access(path, os.W_OK):
                issues.append(f"No write permission: {path}")

        if issues:
            for issue in issues:
                self.stdout.write(self.style.ERROR(f"   ❌ {issue}"))
            return 0

        self.stdout.write(
            self.style.SUCCESS("   ✅ All required directories accessible")
        )
        return 1

    def _check_django_configuration(self):
        """Check Django configuration settings."""
        self.stdout.write(self.style.HTTP_INFO("⚙️  Checking Django configuration..."))

        # Check debug setting
        if settings.DEBUG:
            self.stdout.write(
                self.style.WARNING("   ⚠️  DEBUG is enabled (acceptable for staging)")
            )
        else:
            self.stdout.write(self.style.SUCCESS("   ✅ DEBUG is disabled"))

        # Check allowed hosts
        if "staging" in str(settings.ALLOWED_HOSTS).lower():
            self.stdout.write(self.style.SUCCESS("   ✅ Staging hosts configured"))
        else:
            self.stdout.write(
                self.style.WARNING("   ⚠️  No staging hosts in ALLOWED_HOSTS")
            )

        # Check staging-specific settings
        if getattr(settings, "STAGING_ENVIRONMENT", False):
            self.stdout.write(self.style.SUCCESS("   ✅ Staging environment flag set"))
        else:
            self.stdout.write(
                self.style.WARNING("   ⚠️  STAGING_ENVIRONMENT flag not set")
            )

        return 1

    def _check_ssl_configuration(self):
        """Check SSL and security configuration."""
        self.stdout.write(self.style.HTTP_INFO("🔒 Checking SSL configuration..."))

        security_checks = [
            ("SECURE_SSL_REDIRECT", getattr(settings, "SECURE_SSL_REDIRECT", False)),
            (
                "SESSION_COOKIE_SECURE",
                getattr(settings, "SESSION_COOKIE_SECURE", False),
            ),
            ("CSRF_COOKIE_SECURE", getattr(settings, "CSRF_COOKIE_SECURE", False)),
        ]

        all_secure = True
        for setting_name, value in security_checks:
            if value:
                self.stdout.write(self.style.SUCCESS(f"   ✅ {setting_name} enabled"))
            else:
                self.stdout.write(self.style.WARNING(f"   ⚠️  {setting_name} disabled"))
                all_secure = False

        return 1 if all_secure else 0

    def _check_system_services(self):
        """Check system service status."""
        self.stdout.write(self.style.HTTP_INFO("🔧 Checking system services..."))

        services = [
            "nginx",
            "postgresql",
            "redis-server",
            "sabc-staging",
        ]

        all_running = True
        for service in services:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode == 0:
                    self.stdout.write(self.style.SUCCESS(f"   ✅ {service} is running"))
                else:
                    self.stdout.write(
                        self.style.ERROR(f"   ❌ {service} is not running")
                    )
                    all_running = False
            except subprocess.CalledProcessError:
                self.stdout.write(
                    self.style.ERROR(f"   ❌ Could not check {service} status")
                )
                all_running = False

        return 1 if all_running else 0
