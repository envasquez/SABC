import datetime

from django.shortcuts import render

from ..services.awards_service import AnnualAwardsService
from ..tables import Aoy as AoyTable
from ..tables import BigBass, HeavyStringer


def annual_awards(request, year=0):
    """
    Display annual awards using service layer for business logic.

    Business logic has been extracted to AnnualAwardsService for better
    separation of concerns and maintainability.
    """
    year = year or datetime.date.today().year

    # Use service layer for all award calculations
    aoy_results = AnnualAwardsService.get_angler_of_year_results(year=year)
    heavy_stringer_results = AnnualAwardsService.get_heavy_stringer_winner(year=year)
    big_bass_results = AnnualAwardsService.get_big_bass_winner(year=year)

    # Create table objects for presentation
    aoy_tbl = AoyTable(aoy_results)
    aoy_tbl.order_by = "-total_points"
    hvy_tbl = HeavyStringer(heavy_stringer_results)
    bb_tbl = BigBass(big_bass_results)

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


# Legacy functions - DEPRECATED
# These functions have been replaced by AnnualAwardsService methods
# They are kept temporarily for backward compatibility


def get_aoy_results(year=None):
    """DEPRECATED: Use AnnualAwardsService.get_angler_of_year_results() instead."""
    return AnnualAwardsService.get_angler_of_year_results(year)


def get_heavy_stringer(year=None):
    """DEPRECATED: Use AnnualAwardsService.get_heavy_stringer_winner() instead."""
    return AnnualAwardsService.get_heavy_stringer_winner(year)


def get_big_bass(year=None):
    """DEPRECATED: Use AnnualAwardsService.get_big_bass_winner() instead."""
    return AnnualAwardsService.get_big_bass_winner(year)
