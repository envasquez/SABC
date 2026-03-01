"""Result-related Pydantic models."""

from core.models.base import BaseModel, Decimal


class TournamentStats(BaseModel):
    """Tournament statistics - used by tournament detail page."""

    total_anglers: int = 0
    total_boats: int = 0  # For team format payout calculations
    total_fish: int = 0
    total_weight: Decimal = Decimal("0")
    limits: int = 0
    zeros: int = 0
    buy_ins: int = 0
    biggest_bass: Decimal = Decimal("0")
    heavy_stringer: Decimal = Decimal("0")
