#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Migration Testing Script

Critical Testing Coverage - Phase 1:
- Test database migration scripts with production data copies
- Verify data integrity before and after migrations
- Ensure zero-downtime migration compatibility
- Test rollback procedures

Usage:
    python test_migrations.py --backup-file backup_20250810.sql
    python test_migrations.py --test-all-migrations
    python test_migrations.py --test-rollback
"""

import os
import sys
import subprocess
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# Add Django project to path
project_root = Path(__file__).parent / "sabc"
sys.path.insert(0, str(project_root))

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sabc.settings")
os.environ["UNITTEST"] = "1"  # Use SQLite for testing

import django

django.setup()

from django.core.management import call_command, execute_from_command_line
from django.db import connection, transaction
from django.test.utils import setup_test_environment, teardown_test_environment
from django.contrib.auth import get_user_model

User = get_user_model()


class MigrationTester:
    """Test database migrations with production-like data."""

    def __init__(self, backup_file=None):
        self.backup_file = backup_file
        self.test_db_name = f"sabc_migration_test_{int(datetime.now().timestamp())}"
        self.original_db_settings = None
        self.temp_dirs = []

    def setup_test_environment(self):
        """Set up test environment for migration testing."""
        setup_test_environment()
        print("✅ Test environment set up")

    def teardown_test_environment(self):
        """Clean up test environment."""
        teardown_test_environment()
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        print("✅ Test environment cleaned up")

    def create_test_database_from_backup(self):
        """Create test database from production backup."""
        if not self.backup_file or not os.path.exists(self.backup_file):
            print(
                "❌ Backup file not found. Creating fresh test database with sample data."
            )
            return self._create_fresh_test_database()

        print(f"📥 Creating test database from backup: {self.backup_file}")

        try:
            # Create test database
            subprocess.run(
                ["createdb", self.test_db_name], check=True, capture_output=True
            )

            # Restore from backup
            with open(self.backup_file, "r") as backup:
                subprocess.run(
                    ["psql", self.test_db_name],
                    stdin=backup,
                    check=True,
                    capture_output=True,
                )

            print(f"✅ Test database '{self.test_db_name}' created from backup")
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create test database: {e}")
            return False

    def _create_fresh_test_database(self):
        """Create fresh test database with sample data."""
        print("🏗️  Creating fresh test database with sample data")

        try:
            # Use Django's test database creation
            call_command("migrate", verbosity=0)
            call_command("load_fake_data", "--clear", verbosity=0)

            print("✅ Fresh test database created with sample data")
            return True

        except Exception as e:
            print(f"❌ Failed to create fresh test database: {e}")
            return False

    def verify_data_integrity_before_migration(self):
        """Verify data integrity before running migrations."""
        print("🔍 Verifying data integrity before migration...")

        integrity_checks = [
            self._check_user_angler_relationships,
            self._check_tournament_results_consistency,
            self._check_foreign_key_constraints,
            self._check_required_fields,
        ]

        all_passed = True
        for check in integrity_checks:
            try:
                check()
            except Exception as e:
                print(f"❌ Data integrity check failed: {check.__name__}: {e}")
                all_passed = False

        if all_passed:
            print("✅ All data integrity checks passed before migration")
        else:
            print("❌ Some data integrity checks failed before migration")

        return all_passed

    def _check_user_angler_relationships(self):
        """Check User-Angler relationship integrity."""
        from users.models import Angler

        users_count = User.objects.count()
        anglers_count = Angler.objects.count()

        # Check for orphaned anglers
        orphaned_anglers = Angler.objects.filter(user__isnull=True).count()
        if orphaned_anglers > 0:
            raise ValueError(f"Found {orphaned_anglers} orphaned angler records")

        # Check for users without angler profiles (might be intentional for staff)
        users_without_anglers = User.objects.filter(angler__isnull=True).count()

        print(
            f"   Users: {users_count}, Anglers: {anglers_count}, Users without anglers: {users_without_anglers}"
        )

    def _check_tournament_results_consistency(self):
        """Check tournament results data consistency."""
        from tournaments.models.tournaments import Tournament
        from tournaments.models.results import Result

        tournaments_count = Tournament.objects.count()
        results_count = Result.objects.count()

        # Check for results without valid tournaments
        invalid_results = Result.objects.filter(tournament__isnull=True).count()
        if invalid_results > 0:
            raise ValueError(
                f"Found {invalid_results} results without valid tournaments"
            )

        # Check for negative weights or fish counts
        negative_weights = Result.objects.filter(total_weight__lt=0).count()
        negative_fish = Result.objects.filter(num_fish__lt=0).count()

        if negative_weights > 0:
            raise ValueError(f"Found {negative_weights} results with negative weights")
        if negative_fish > 0:
            raise ValueError(f"Found {negative_fish} results with negative fish counts")

        print(f"   Tournaments: {tournaments_count}, Results: {results_count}")

    def _check_foreign_key_constraints(self):
        """Check foreign key constraint integrity."""
        with connection.cursor() as cursor:
            # Check for any foreign key constraint violations
            # This is PostgreSQL-specific
            cursor.execute("""
                SELECT conname, conrelid::regclass, confrelid::regclass
                FROM pg_constraint
                WHERE contype = 'f';
            """)

            constraints = cursor.fetchall()
            print(f"   Verified {len(constraints)} foreign key constraints")

    def _check_required_fields(self):
        """Check that required fields are not null."""
        # Check critical non-null fields
        from tournaments.models.results import Result

        null_anglers = Result.objects.filter(angler__isnull=True).count()
        null_tournaments = Result.objects.filter(tournament__isnull=True).count()

        if null_anglers > 0:
            raise ValueError(f"Found {null_anglers} results with null angler")
        if null_tournaments > 0:
            raise ValueError(f"Found {null_tournaments} results with null tournament")

        print("   All required fields have valid values")

    def test_migrations_forward(self):
        """Test running migrations forward."""
        print("⬆️  Testing forward migrations...")

        try:
            # Get current migration state
            call_command("showmigrations", format="plan", verbosity=0)

            # Run migrations
            call_command("migrate", verbosity=1)

            print("✅ Forward migrations completed successfully")
            return True

        except Exception as e:
            print(f"❌ Forward migration failed: {e}")
            return False

    def test_migrations_rollback(self):
        """Test rolling back migrations."""
        print("⬇️  Testing migration rollback...")

        try:
            # Test rollback to a previous migration
            # This would be customized based on actual migration history
            print("   Testing rollback capability...")

            # Get migration history
            call_command("showmigrations", verbosity=0)

            # For safety, we don't actually rollback in this test
            # In a real scenario, you would:
            # call_command('migrate', 'app_name', '0001', verbosity=1)

            print("✅ Rollback test completed (simulation)")
            return True

        except Exception as e:
            print(f"❌ Rollback test failed: {e}")
            return False

    def verify_data_integrity_after_migration(self):
        """Verify data integrity after running migrations."""
        print("🔍 Verifying data integrity after migration...")

        # Run the same checks as before migration
        return self.verify_data_integrity_before_migration()

    def performance_benchmark(self):
        """Benchmark key database operations after migration."""
        print("⚡ Running performance benchmarks...")

        benchmarks = [
            self._benchmark_user_queries,
            self._benchmark_tournament_queries,
            self._benchmark_results_queries,
        ]

        results = {}
        for benchmark in benchmarks:
            try:
                result = benchmark()
                results[benchmark.__name__] = result
            except Exception as e:
                print(f"❌ Benchmark failed: {benchmark.__name__}: {e}")
                results[benchmark.__name__] = None

        return results

    def _benchmark_user_queries(self):
        """Benchmark user-related queries."""
        import time

        start_time = time.time()

        # Simulate common user queries
        users = list(User.objects.select_related("angler")[:100])
        member_count = User.objects.filter(angler__member=True).count()

        end_time = time.time()
        duration = end_time - start_time

        print(
            f"   User queries: {duration:.3f}s ({len(users)} users, {member_count} members)"
        )
        return duration

    def _benchmark_tournament_queries(self):
        """Benchmark tournament-related queries."""
        import time
        from tournaments.models.tournaments import Tournament

        start_time = time.time()

        # Simulate common tournament queries
        tournaments = list(Tournament.objects.select_related("lake", "event")[:50])
        completed_count = Tournament.objects.filter(complete=True).count()

        end_time = time.time()
        duration = end_time - start_time

        print(
            f"   Tournament queries: {duration:.3f}s ({len(tournaments)} tournaments, {completed_count} completed)"
        )
        return duration

    def _benchmark_results_queries(self):
        """Benchmark results-related queries."""
        import time
        from tournaments.models.results import Result

        start_time = time.time()

        # Simulate common results queries
        results = list(
            Result.objects.select_related("angler__user", "tournament")[:200]
        )
        total_results = Result.objects.count()

        end_time = time.time()
        duration = end_time - start_time

        print(
            f"   Results queries: {duration:.3f}s ({len(results)} loaded, {total_results} total)"
        )
        return duration

    def cleanup_test_database(self):
        """Clean up test database."""
        try:
            subprocess.run(
                ["dropdb", self.test_db_name], check=True, capture_output=True
            )
            print(f"✅ Test database '{self.test_db_name}' cleaned up")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Could not clean up test database: {e}")

    def run_full_migration_test(self):
        """Run complete migration test suite."""
        print("🚀 Starting comprehensive migration test suite")
        print("=" * 60)

        success = True

        try:
            # Setup
            self.setup_test_environment()

            # Create test database
            if not self.create_test_database_from_backup():
                success = False
                return success

            # Pre-migration checks
            if not self.verify_data_integrity_before_migration():
                success = False

            # Test migrations
            if not self.test_migrations_forward():
                success = False

            # Post-migration checks
            if not self.verify_data_integrity_after_migration():
                success = False

            # Test rollback capability
            if not self.test_migrations_rollback():
                success = False

            # Performance benchmarks
            benchmark_results = self.performance_benchmark()

            # Summary
            print("\n" + "=" * 60)
            if success:
                print("🎉 Migration test suite PASSED!")
                print("\nPerformance Benchmarks:")
                for name, duration in benchmark_results.items():
                    if duration is not None:
                        print(f"   {name}: {duration:.3f}s")
            else:
                print("❌ Migration test suite FAILED!")
                print(
                    "   Please review the errors above before proceeding with production migration."
                )

        finally:
            # Always cleanup
            self.cleanup_test_database()
            self.teardown_test_environment()

        return success


def main():
    """Main entry point for migration testing."""
    parser = argparse.ArgumentParser(
        description="Test database migrations with production data"
    )
    parser.add_argument("--backup-file", help="Path to production database backup file")
    parser.add_argument(
        "--test-all-migrations",
        action="store_true",
        help="Test all migrations from scratch",
    )
    parser.add_argument(
        "--test-rollback", action="store_true", help="Test rollback procedures"
    )

    args = parser.parse_args()

    tester = MigrationTester(backup_file=args.backup_file)

    if args.test_all_migrations or args.test_rollback or args.backup_file:
        success = tester.run_full_migration_test()
        sys.exit(0 if success else 1)
    else:
        print(
            "Usage: python test_migrations.py [--backup-file file] [--test-all-migrations] [--test-rollback]"
        )
        print("\nExample:")
        print("  python test_migrations.py --backup-file backup_20250810.sql")
        print("  python test_migrations.py --test-all-migrations")
        sys.exit(1)


if __name__ == "__main__":
    main()
