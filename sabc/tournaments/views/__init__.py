import datetime

from django.shortcuts import render

from ..services.awards_service import AnnualAwardsService


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

    # Pass raw data to template instead of table objects
    return render(
        request,
        "tournaments/annual_awards.html",
        {
            "title": f"{year} awards".title(),
            "aoy_results": aoy_results,
            "heavy_stringer_results": heavy_stringer_results,
            "big_bass_results": big_bass_results,
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
