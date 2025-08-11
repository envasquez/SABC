# Database Optimization Module for SABC
# Performance improvements for Phase 2: Performance & Reliability

import logging
import time
from functools import wraps

from django.core.cache import cache
from django.db import models
from django.db.models import Count, F, Max, Prefetch, Q, Sum

logger = logging.getLogger("sabc.performance")


def log_query_performance(func):
    """Decorator to log query performance metrics."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time

        if execution_time > 0.5:  # Log slow queries (> 500ms)
            logger.warning(
                f"Slow query detected in {func.__name__}: {execution_time:.2f}s"
            )
        else:
            logger.debug(f"Query {func.__name__} executed in {execution_time:.3f}s")

        return result

    return wrapper


class OptimizedQueryMixin:
    """Mixin for optimized database queries with caching and prefetching."""

    @classmethod
    def get_with_related(cls, **filters):
        """Get objects with all related fields prefetched."""
        queryset = cls.objects.filter(**filters)

        # Automatically select/prefetch related fields based on model
        if hasattr(cls, "_select_related"):
            queryset = queryset.select_related(*cls._select_related)
        if hasattr(cls, "_prefetch_related"):
            queryset = queryset.prefetch_related(*cls._prefetch_related)

        return queryset

    @classmethod
    def get_cached(cls, cache_key, timeout=300, **filters):
        """Get objects with caching support."""
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        result = cls.objects.filter(**filters)
        cache.set(cache_key, result, timeout)
        return result


# Optimized query functions for tournaments
@log_query_performance
def get_tournament_with_results(tournament_id):
    """Get tournament with all related data efficiently."""
    from tournaments.models.results import Result
    from tournaments.models.tournaments import Tournament

    # Use select_related for one-to-one and foreign keys
    # Use prefetch_related for reverse foreign keys and many-to-many
    tournament = (
        Tournament.objects.select_related(
            "lake", "ramp", "rules", "payout_multiplier", "event"
        )
        .prefetch_related(
            Prefetch(
                "result_set",
                queryset=Result.objects.select_related("angler__user").order_by(
                    "place_finish"
                ),
            )
        )
        .get(id=tournament_id)
    )

    return tournament


@log_query_performance
def get_aoy_results_optimized(year):
    """Optimized version of get_aoy_results with better query performance."""
    from django.db.models import Count, Max, Sum
    from tournaments.models.results import Result

    # Single aggregated query instead of multiple iterations
    results = (
        Result.objects.filter(
            tournament__event__year=year,
            angler__user__is_active=True,
            angler__member=True,
        )
        .select_related("angler__user", "tournament")
        .values("angler__user__first_name", "angler__user__last_name", "angler__id")
        .annotate(
            total_points=Sum("points"),
            total_weight=Sum("total_weight"),
            total_fish=Sum("num_fish"),
            events=Count("tournament", distinct=True),
            best_finish=Max("place_finish"),
        )
        .order_by("-total_points", "-total_weight")
    )

    # Format results for compatibility
    formatted_results = []
    for r in results:
        formatted_results.append(
            {
                "angler": f"{r['angler__user__first_name']} {r['angler__user__last_name']}",
                "angler_id": r["angler__id"],
                "total_points": r["total_points"] or 0,
                "total_weight": r["total_weight"] or 0,
                "total_fish": r["total_fish"] or 0,
                "events": r["events"] or 0,
                "best_finish": r["best_finish"],
            }
        )

    return formatted_results


@log_query_performance
def get_tournament_list_optimized(year=None):
    """Get tournaments with minimal queries."""
    from tournaments.models.tournaments import Tournament

    queryset = Tournament.objects.select_related("lake", "event", "rules").annotate(
        participant_count=Count("result", distinct=True), has_results=Count("result")
    )

    if year:
        queryset = queryset.filter(event__year=year)

    return queryset.order_by("-event__date")


@log_query_performance
def get_recent_results_optimized(limit=10):
    """Get recent results with all related data."""
    from tournaments.models.results import Result

    return (
        Result.objects.select_related(
            "angler__user", "tournament__lake", "tournament__event"
        )
        .filter(tournament__complete=True)
        .order_by("-tournament__event__date", "place_finish")[:limit]
    )


@log_query_performance
def get_roster_optimized(member_type="all"):
    """Get roster with optimized queries."""
    from tournaments.models.results import Result
    from users.models import Angler

    queryset = Angler.objects.select_related("user").prefetch_related(
        Prefetch(
            "result_set", queryset=Result.objects.select_related("tournament__event")
        )
    )

    if member_type == "members":
        queryset = queryset.filter(member=True)
    elif member_type == "guests":
        queryset = queryset.filter(member=False)

    return queryset.order_by("user__last_name", "user__first_name")


# Database index recommendations
DATABASE_INDEX_RECOMMENDATIONS = {
    "tournaments_result": [
        # Composite indexes for common query patterns
        models.Index(
            fields=["tournament", "place_finish"], name="idx_tournament_place"
        ),
        models.Index(fields=["angler", "tournament"], name="idx_angler_tournament"),
        models.Index(
            fields=["tournament", "-total_weight"], name="idx_tournament_weight"
        ),
        models.Index(
            fields=["tournament", "buy_in", "disqualified"],
            name="idx_tournament_status",
        ),
    ],
    "tournaments_tournament": [
        models.Index(fields=["event", "complete"], name="idx_event_complete"),
        models.Index(fields=["complete", "-event"], name="idx_complete_event_desc"),
    ],
    "tournaments_events": [
        models.Index(fields=["year", "date"], name="idx_year_date"),
        models.Index(fields=["type", "year"], name="idx_type_year"),
    ],
    "users_angler": [
        models.Index(fields=["member", "user"], name="idx_member_user"),
    ],
}


# Query optimization tips
OPTIMIZATION_TIPS = """
Database Optimization Guidelines for SABC:

1. Use select_related() for ForeignKey and OneToOne relationships
2. Use prefetch_related() for ManyToMany and reverse ForeignKey relationships
3. Use only() and defer() to limit fields retrieved
4. Use aggregate functions instead of Python loops
5. Add database indexes on frequently queried fields
6. Use database views for complex queries
7. Implement query result caching for expensive operations
8. Monitor slow queries with Django Debug Toolbar
9. Use bulk operations (bulk_create, bulk_update) when possible
10. Avoid N+1 queries by prefetching related objects

Common Problem Areas Identified:
- get_aoy_results: Multiple iterations over same queryset
- Tournament list views: Missing prefetch for results
- Calendar view: Multiple queries for events
- Result calculations: Inefficient aggregations
"""


def apply_database_indexes():
    """
    Generate migration to add recommended database indexes.
    Run: python manage.py makemigrations --empty tournaments
    Then add these indexes to the migration.
    """
    migration_content = """
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', 'XXXX_previous_migration'),
    ]

    operations = [
        # Result model indexes
        migrations.AddIndex(
            model_name='result',
            index=models.Index(fields=['tournament', 'place_finish'], name='idx_tournament_place'),
        ),
        migrations.AddIndex(
            model_name='result',
            index=models.Index(fields=['angler', 'tournament'], name='idx_angler_tournament'),
        ),
        migrations.AddIndex(
            model_name='result',
            index=models.Index(fields=['tournament', '-total_weight'], name='idx_tournament_weight'),
        ),
        migrations.AddIndex(
            model_name='result',
            index=models.Index(fields=['tournament', 'buy_in', 'disqualified'], name='idx_tournament_status'),
        ),

        # Tournament model indexes
        migrations.AddIndex(
            model_name='tournament',
            index=models.Index(fields=['event', 'complete'], name='idx_event_complete'),
        ),
        migrations.AddIndex(
            model_name='tournament',
            index=models.Index(fields=['complete', '-event'], name='idx_complete_event_desc'),
        ),

        # Events model indexes
        migrations.AddIndex(
            model_name='events',
            index=models.Index(fields=['year', 'date'], name='idx_year_date'),
        ),
        migrations.AddIndex(
            model_name='events',
            index=models.Index(fields=['type', 'year'], name='idx_type_year'),
        ),
    ]
    """
    return migration_content
