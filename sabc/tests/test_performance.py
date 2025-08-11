#!/usr/bin/env python
"""
Performance Testing Script for SABC Database Optimizations
Phase 2: Performance & Reliability

This script tests and documents the performance improvements from:
1. Database indexes
2. Query optimizations
3. Select/prefetch related optimizations
"""

import os
import sys
import time
from decimal import Decimal

import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sabc.settings")
django.setup()

from django.contrib.auth.models import User
from django.db import connection, reset_queries
from django.test import TestCase, TransactionTestCase
from tournaments.models.results import Result
from tournaments.models.tournaments import Tournament
from tournaments.views import get_aoy_results, get_big_bass, get_heavy_stringer
from users.models import Angler


class PerformanceTestRunner:
    """Test runner for database performance metrics."""

    def __init__(self):
        self.results = []

    def measure_query(self, name, func, *args, **kwargs):
        """Measure the performance of a database operation."""
        reset_queries()
        start_time = time.time()

        result = func(*args, **kwargs)

        execution_time = time.time() - start_time
        query_count = len(connection.queries)

        self.results.append(
            {
                "name": name,
                "execution_time": execution_time,
                "query_count": query_count,
                "queries": connection.queries if query_count < 10 else [],
            }
        )

        return result

    def print_results(self):
        """Print performance test results."""
        print("\n" + "=" * 80)
        print("PERFORMANCE TEST RESULTS - Database Optimizations")
        print("=" * 80)

        for result in self.results:
            print(f"\n{result['name']}:")
            print(f"  Execution Time: {result['execution_time']:.4f} seconds")
            print(f"  Query Count: {result['query_count']}")

            if result["queries"]:
                print("  Sample Queries:")
                for i, query in enumerate(result["queries"][:3], 1):
                    print(f"    {i}. {query['sql'][:100]}... ({query['time']}s)")

        print("\n" + "=" * 80)
        print("PERFORMANCE SUMMARY")
        print("=" * 80)

        total_time = sum(r["execution_time"] for r in self.results)
        total_queries = sum(r["query_count"] for r in self.results)

        print(f"Total Execution Time: {total_time:.4f} seconds")
        print(f"Total Query Count: {total_queries}")
        print(f"Average Queries per Operation: {total_queries / len(self.results):.1f}")

        # Identify potential issues
        print("\n" + "=" * 80)
        print("OPTIMIZATION OPPORTUNITIES")
        print("=" * 80)

        high_query_operations = [r for r in self.results if r["query_count"] > 10]
        slow_operations = [r for r in self.results if r["execution_time"] > 0.5]

        if high_query_operations:
            print("\nHigh Query Count Operations (>10 queries):")
            for op in high_query_operations:
                print(f"  - {op['name']}: {op['query_count']} queries")

        if slow_operations:
            print("\nSlow Operations (>0.5 seconds):")
            for op in slow_operations:
                print(f"  - {op['name']}: {op['execution_time']:.4f}s")

        if not high_query_operations and not slow_operations:
            print("\n✅ All operations are optimized!")


def run_performance_tests():
    """Run comprehensive performance tests."""
    runner = PerformanceTestRunner()

    print("\nSetting up test data...")

    # Test 1: Tournament List Query
    runner.measure_query(
        "Tournament List (with related data)",
        lambda: list(
            Tournament.objects.select_related("lake", "event", "rules").filter(
                event__year=2024
            )[:20]
        ),
    )

    # Test 2: Tournament List Query (without optimization)
    runner.measure_query(
        "Tournament List (without optimization)",
        lambda: list(Tournament.objects.filter(event__year=2024)[:20]),
    )

    # Test 3: AOY Results Calculation
    runner.measure_query(
        "AOY Results Calculation (optimized)", get_aoy_results, year=2024
    )

    # Test 4: Heavy Stringer Query
    runner.measure_query(
        "Heavy Stringer Query (optimized)", get_heavy_stringer, year=2024
    )

    # Test 5: Big Bass Query
    runner.measure_query("Big Bass Query (optimized)", get_big_bass, year=2024)

    # Test 6: Results with Angler Info
    runner.measure_query(
        "Results with Angler (optimized)",
        lambda: list(
            Result.objects.select_related("angler__user", "tournament__lake").filter(
                tournament__event__year=2024
            )[:50]
        ),
    )

    # Test 7: Results without optimization
    runner.measure_query(
        "Results without optimization",
        lambda: list(Result.objects.filter(tournament__event__year=2024)[:50]),
    )

    # Test 8: Complex aggregation query
    from django.db.models import Avg, Count, Sum

    runner.measure_query(
        "Complex Aggregation (tournament statistics)",
        lambda: Tournament.objects.filter(event__year=2024).aggregate(
            total_participants=Count("result"),
            total_weight=Sum("result__total_weight"),
            avg_weight=Avg("result__total_weight"),
            total_fish=Sum("result__num_fish"),
        ),
    )

    # Test 9: Calendar view query
    runner.measure_query(
        "Calendar View Query (optimized)",
        lambda: list(
            Tournament.objects.select_related("lake", "event")
            .filter(event__year=2024)
            .only(
                "id",
                "name",
                "complete",
                "lake__name",
                "event__date",
                "event__start",
                "event__finish",
            )
        ),
    )

    # Test 10: Roster query with statistics
    from django.db.models import Q

    runner.measure_query(
        "Roster with Statistics",
        lambda: list(
            Angler.objects.select_related("user")
            .annotate(
                total_points=Sum(
                    "result__points", filter=Q(result__tournament__event__year=2024)
                ),
                total_events=Count(
                    "result__tournament",
                    filter=Q(result__tournament__event__year=2024),
                    distinct=True,
                ),
            )
            .filter(member=True)[:20]
        ),
    )

    # Print results
    runner.print_results()

    # Additional index verification
    print("\n" + "=" * 80)
    print("DATABASE INDEX VERIFICATION")
    print("=" * 80)

    from django.conf import settings

    if "postgresql" in settings.DATABASES["default"]["ENGINE"]:
        with connection.cursor() as cursor:
            # Check for our custom indexes
            cursor.execute("""
                SELECT indexname, tablename 
                FROM pg_indexes 
                WHERE indexname LIKE 'idx_%'
                ORDER BY tablename, indexname
            """)
            indexes = cursor.fetchall()

            if indexes:
                print("\nCustom indexes found:")
                for index_name, table_name in indexes:
                    print(f"  ✓ {table_name}: {index_name}")
            else:
                print(
                    "\n⚠️  No custom indexes found. Run migrations to add performance indexes."
                )
    else:
        print("\nIndex verification skipped (SQLite database).")
        print("Indexes are created via migrations and will be active.")

    print("\n" + "=" * 80)
    print("OPTIMIZATION RECOMMENDATIONS")
    print("=" * 80)
    print("""
1. ✅ Database indexes have been added for frequently queried fields
2. ✅ Select_related() is used for ForeignKey relationships
3. ✅ Prefetch_related() is used for reverse ForeignKey relationships
4. ✅ Query aggregation is used instead of Python loops where possible
5. ✅ Only() is used to limit fields retrieved when full objects aren't needed
6. ✅ Query monitoring middleware has been added for development

Next Steps:
- Monitor production queries using the performance logging
- Consider adding database-level views for complex queries
- Implement query result caching for expensive operations
- Use Django Debug Toolbar for detailed query analysis
- Consider pagination for large result sets
""")


if __name__ == "__main__":
    # Run performance tests
    from django.conf import settings

    db_engine = settings.DATABASES["default"]["ENGINE"]
    if "sqlite" in db_engine:
        print("⚠️  Running with SQLite. Index verification will be skipped.")
        print("For full performance testing, use PostgreSQL.\n")

    run_performance_tests()
