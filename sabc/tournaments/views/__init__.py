import datetime
from decimal import Decimal
from typing import Optional

from django.db.models import QuerySet
from django.shortcuts import HttpResponse, render

from ..models.results import Result
from ..tables import Aoy as AoyTable
from ..tables import BigBass, HeavyStringer


def annual_awards(request, year: int = 0) -> HttpResponse:
    year = year or datetime.date.today().year
    aoy_tbl: AoyTable = AoyTable(get_aoy_results(year=year))
    aoy_tbl.order_by = "-total_points"
    hvy_tbl: HeavyStringer = HeavyStringer(get_heavy_stringer(year=year))
    bb_tbl: BigBass = BigBass(get_big_bass(year=year))
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


def get_aoy_results(year: int = datetime.date.today().year) -> list:
    all_results: QuerySet = Result.objects.filter(
        tournament__event__year=year, angler__user__is_active=True, angler__member=True
    )
    anglers: list = []
    for result in all_results:
        if all((result.angler not in anglers, result.angler.member)):
            anglers.append(result.angler)

    results: list = []
    for angler in anglers:
        stats = {
            "angler": angler.user.get_full_name(),
            "total_points": sum(r.points for r in all_results if r.angler == angler),
            "total_weight": sum(
                r.total_weight for r in all_results if r.angler == angler
            ),
            "total_fish": sum(r.num_fish for r in all_results if r.angler == angler),
            "events": sum(1 for r in all_results if r.angler == angler),
        }
        results.append(stats)
    return results


def get_heavy_stringer(year: int = datetime.date.today().year) -> list:
    result: Optional[Result] = (
        Result.objects.filter(
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


def get_big_bass(year=datetime.date.today().year) -> list:
    query: Optional[Result] = (
        Result.objects.filter(
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
