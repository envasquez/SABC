import datetime
from decimal import Decimal
from typing import Optional

from django.db.models import QuerySet
from django.shortcuts import render

from ..models.results import Result
from ..tables import Aoy as AoyTable
from ..tables import BigBass, HeavyStringer


def annual_awards(request, year=0):
    year = year or datetime.date.today().year
    aoy_tbl = AoyTable(get_aoy_results(year=year))
    aoy_tbl.order_by = "-total_points"
    hvy_tbl = HeavyStringer(get_heavy_stringer(year=year))
    bb_tbl = BigBass(get_big_bass(year=year))
    return render(
        request,
        "tournaments/annual_awards.html",
        {
            "title": f"{year} awards".title(),
            "aoy_tbl": aoy_tbl,
            "hvy_tbl": hvy_tbl,
            "bb_tbl": bb_tbl,
            "year": year,
        },
    )


def get_aoy_results(year=datetime.date.today().year):
    # Optimized version using aggregation and select_related
    from django.db.models import Count, Sum

    all_results = Result.objects.filter(
        tournament__event__year=year, angler__user__is_active=True, angler__member=True
    ).select_related("angler__user", "tournament__event")

    # Use dictionary to aggregate by angler efficiently
    angler_stats = {}
    for result in all_results:
        angler_key = result.angler.pk
        if angler_key not in angler_stats:
            angler_stats[angler_key] = {
                "angler": result.angler.user.get_full_name(),
                "total_points": 0,
                "total_weight": Decimal("0"),
                "total_fish": 0,
                "events": 0,
            }

        angler_stats[angler_key]["total_points"] += result.points or 0
        angler_stats[angler_key]["total_weight"] += result.total_weight or Decimal("0")
        angler_stats[angler_key]["total_fish"] += result.num_fish or 0
        angler_stats[angler_key]["events"] += 1

    # Convert to list and ensure decimal to float conversion for serialization
    results = []
    for stats in angler_stats.values():
        stats["total_weight"] = float(stats["total_weight"])
        results.append(stats)

    return results


def get_heavy_stringer(year=datetime.date.today().year):
    # Optimized with select_related to avoid additional queries
    result = (
        Result.objects.select_related(
            "angler__user", "tournament__lake", "tournament__event"
        )
        .filter(
            tournament__event__year=year,
            angler__member=True,
            angler__user__is_active=True,
            total_weight__gt=Decimal("0"),
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


def get_big_bass(year=datetime.date.today().year):
    # Optimized with select_related to avoid additional queries
    query: Optional[Result] = (
        Result.objects.select_related(
            "angler__user", "tournament__lake", "tournament__event"
        )
        .filter(
            tournament__event__year=year,
            angler__user__is_active=True,
            big_bass_weight__gte=Decimal("5.0"),
        )
        .order_by("-big_bass_weight")
        .first()
    )
    return (
        [
            {
                "angler": query.angler,
                "weight": query.big_bass_weight,
                "tournament": query.tournament,
            }
        ]
        if query
        else []
    )
