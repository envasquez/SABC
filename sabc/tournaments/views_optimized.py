# Optimized views for tournaments with database performance improvements
import datetime
from decimal import Decimal
from typing import Optional

from core.cache_utils import CacheManager
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Count, F, Max, Prefetch, Q, Sum
from django.views.generic import DetailView, ListView
from users.models import Angler

from tournaments.models.events import Events
from tournaments.models.results import Result, TeamResult
from tournaments.models.tournaments import Tournament


class OptimizedTournamentListView(ListView):
    """Optimized tournament list with prefetching and caching."""

    model = Tournament
    template_name = "tournaments/tournament_list.html"
    context_object_name = "tournaments"
    paginate_by = 20

    def get_queryset(self):
        """Get tournaments with all related data prefetched."""
        year = self.request.GET.get("year", datetime.date.today().year)

        # Check cache first
        cached_result = CacheManager.get("tournament_list", year=year)
        if cached_result is not None:
            return cached_result

        # Optimized query with select_related and annotations
        queryset = (
            Tournament.objects.select_related(
                "lake", "event", "rules", "payout_multiplier"
            )
            .annotate(
                participant_count=Count("result", distinct=True),
                has_results=Count("result"),
                avg_weight=Sum("result__total_weight") / Count("result", distinct=True),
            )
            .filter(event__year=year)
            .order_by("-event__date")
        )

        # Cache the queryset
        CacheManager.set("tournament_list", queryset, year=year)
        return queryset


class OptimizedTournamentDetailView(DetailView):
    """Optimized tournament detail with efficient result loading."""

    model = Tournament
    template_name = "tournaments/tournament_detail.html"

    def get_object(self):
        """Get tournament with all results prefetched."""
        tournament_id = self.kwargs["pk"]

        # Single query with all related data
        tournament = (
            Tournament.objects.select_related(
                "lake", "ramp", "rules", "payout_multiplier", "event"
            )
            .prefetch_related(
                Prefetch(
                    "result_set",
                    queryset=Result.objects.select_related("angler__user")
                    .filter(buy_in=False, disqualified=False)
                    .order_by("place_finish"),
                    to_attr="valid_results",
                ),
                Prefetch(
                    "teamresult_set",
                    queryset=TeamResult.objects.select_related(
                        "result_1__angler__user", "result_2__angler__user"
                    ).order_by("place_finish"),
                    to_attr="team_results",
                ),
            )
            .get(id=tournament_id)
        )

        return tournament

    def get_context_data(self, **kwargs):
        """Add optimized statistics to context."""
        context = super().get_context_data(**kwargs)
        tournament = self.object

        # Use prefetched results for statistics
        if hasattr(tournament, "valid_results"):
            context["total_participants"] = len(tournament.valid_results)
            context["total_weight"] = sum(
                r.total_weight for r in tournament.valid_results
            )
            context["total_fish"] = sum(r.num_fish for r in tournament.valid_results)

            # Big bass winner (already in memory)
            big_bass_results = [
                r for r in tournament.valid_results if r.big_bass_weight >= Decimal("5")
            ]
            if big_bass_results:
                context["big_bass_winner"] = max(
                    big_bass_results, key=lambda r: r.big_bass_weight
                )

        return context


def get_aoy_results_optimized(year=None):
    """
    Optimized Angler of the Year results using aggregation.
    Replaces multiple iterations with a single aggregated query.
    """
    if year is None:
        year = datetime.date.today().year

    # Check cache first
    cached_result = CacheManager.get("aoy_results", year=year)
    if cached_result is not None:
        return cached_result

    # Single aggregated query for all statistics
    results = (
        Result.objects.filter(
            tournament__event__year=year,
            angler__user__is_active=True,
            angler__member=True,
            tournament__complete=True,
            tournament__points_count=True,
        )
        .values("angler__id", "angler__user__first_name", "angler__user__last_name")
        .annotate(
            total_points=Sum("points"),
            total_weight=Sum("total_weight"),
            total_fish=Sum("num_fish"),
            events=Count("tournament", distinct=True),
            best_finish=Max("place_finish"),
            avg_weight=Sum("total_weight") / Count("tournament", distinct=True),
        )
        .order_by("-total_points", "-total_weight")
    )

    # Format results
    formatted_results = []
    for r in results:
        formatted_results.append(
            {
                "angler": f"{r['angler__user__first_name']} {r['angler__user__last_name']}",
                "angler_id": r["angler__id"],
                "total_points": r["total_points"] or 0,
                "total_weight": float(r["total_weight"] or 0),
                "total_fish": r["total_fish"] or 0,
                "events": r["events"] or 0,
                "best_finish": r["best_finish"],
                "avg_weight": float(r["avg_weight"] or 0),
            }
        )

    # Cache the results
    CacheManager.set("aoy_results", formatted_results, year=year)
    return formatted_results


def get_heavy_stringer_optimized(year=None):
    """Optimized heavy stringer query."""
    if year is None:
        year = datetime.date.today().year

    # Use select_related to avoid additional queries
    result = (
        Result.objects.select_related(
            "angler__user", "tournament__lake", "tournament__event"
        )
        .filter(
            tournament__event__year=year,
            angler__member=True,
            angler__user__is_active=True,
            total_weight__gt=Decimal("0"),
            tournament__complete=True,
        )
        .order_by("-total_weight")
        .first()
    )

    if result:
        return [
            {
                "angler": result.angler,
                "weight": result.total_weight,
                "fish": result.num_fish,
                "tournament": result.tournament,
            }
        ]
    return []


def get_big_bass_optimized(year=None):
    """Optimized big bass query."""
    if year is None:
        year = datetime.date.today().year

    # Use select_related to avoid additional queries
    result = (
        Result.objects.select_related(
            "angler__user", "tournament__lake", "tournament__event"
        )
        .filter(
            tournament__event__year=year,
            angler__user__is_active=True,
            big_bass_weight__gte=Decimal("5.0"),
            tournament__complete=True,
        )
        .order_by("-big_bass_weight")
        .first()
    )

    if result:
        return [
            {
                "angler": result.angler,
                "weight": result.big_bass_weight,
                "tournament": result.tournament,
            }
        ]
    return []


def get_calendar_events_optimized(year):
    """Get calendar events with minimal queries."""
    # Single query for tournaments with related data
    tournaments = (
        Tournament.objects.select_related("lake", "event")
        .filter(event__year=year)
        .only(
            "id",
            "name",
            "complete",
            "lake__name",
            "event__date",
            "event__start",
            "event__finish",
        )
    )

    # Single query for calendar events
    from tournaments.models.calendar_events import CalendarEvent

    calendar_events = CalendarEvent.objects.filter(date__year=year).only(
        "date", "title", "description", "category"
    )

    return tournaments, calendar_events


class OptimizedRosterView(ListView):
    """Optimized roster view with prefetching."""

    model = Angler
    template_name = "users/roster.html"
    context_object_name = "anglers"

    def get_queryset(self):
        """Get anglers with statistics prefetched."""
        current_year = datetime.date.today().year

        # Annotate with current year statistics
        queryset = (
            Angler.objects.select_related("user")
            .annotate(
                total_points=Sum(
                    "result__points",
                    filter=Q(result__tournament__event__year=current_year),
                ),
                total_events=Count(
                    "result__tournament",
                    filter=Q(result__tournament__event__year=current_year),
                    distinct=True,
                ),
                total_weight=Sum(
                    "result__total_weight",
                    filter=Q(result__tournament__event__year=current_year),
                ),
            )
            .order_by("user__last_name", "user__first_name")
        )

        # Filter by member type if specified
        member_type = self.request.GET.get("type", "all")
        if member_type == "members":
            queryset = queryset.filter(member=True)
        elif member_type == "guests":
            queryset = queryset.filter(member=False)

        return queryset


# Performance monitoring middleware
class QueryCountDebugMiddleware:
    """Middleware to log query counts for performance monitoring."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings
        from django.db import connection, reset_queries

        if settings.DEBUG:
            reset_queries()

            response = self.get_response(request)

            num_queries = len(connection.queries)
            if num_queries > 10:  # Log if more than 10 queries
                import logging

                logger = logging.getLogger("sabc.performance")
                logger.warning(
                    f"High query count on {request.path}: {num_queries} queries"
                )

                # Log slow queries
                for query in connection.queries:
                    if float(query["time"]) > 0.1:  # Queries slower than 100ms
                        logger.warning(
                            f"Slow query ({query['time']}s): {query['sql'][:200]}"
                        )

            return response

        return self.get_response(request)
