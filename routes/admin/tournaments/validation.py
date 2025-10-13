"""Validation helpers for tournament result entry."""

from decimal import Decimal
from typing import Optional, Tuple

# Tournament validation constants
MAX_TOTAL_WEIGHT = 50.0  # Maximum total weight for a 5-fish limit (lbs)
MAX_BIG_BASS_WEIGHT = 15.0  # Maximum single bass weight (world record ~22 lbs, but rare)
MAX_AVG_FISH_WEIGHT = 10.0  # Maximum average weight per fish (lbs)
MIN_AVG_FISH_WEIGHT = 0.5  # Minimum average weight per fish (lbs)


def validate_tournament_result(
    num_fish: int,
    total_weight: float,
    big_bass_weight: float,
    dead_fish_penalty: int,
    fish_limit: int = 5,
) -> Tuple[bool, Optional[str]]:
    """
    Validate tournament result data for realistic values.

    Args:
        num_fish: Number of fish caught
        total_weight: Total weight in pounds
        big_bass_weight: Weight of biggest bass in pounds
        dead_fish_penalty: Number of dead fish
        fish_limit: Maximum allowed fish (default 5)

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate fish count
    if num_fish < 0:
        return False, "Number of fish cannot be negative"

    if num_fish > fish_limit:
        return False, f"Number of fish cannot exceed limit of {fish_limit}"

    # Validate total weight
    if total_weight < 0:
        return False, "Total weight cannot be negative"

    if total_weight > MAX_TOTAL_WEIGHT:
        return False, f"Total weight exceeds reasonable maximum ({MAX_TOTAL_WEIGHT} lbs)"

    # Validate big bass weight
    if big_bass_weight < 0:
        return False, "Big bass weight cannot be negative"

    if big_bass_weight > MAX_BIG_BASS_WEIGHT:
        return False, f"Big bass weight exceeds reasonable maximum ({MAX_BIG_BASS_WEIGHT} lbs)"

    # Big bass can't exceed total weight
    if big_bass_weight > total_weight:
        return False, "Big bass weight cannot exceed total weight"

    # Validate dead fish penalty
    if dead_fish_penalty < 0:
        return False, "Dead fish penalty cannot be negative"

    if dead_fish_penalty > num_fish:
        return False, "Dead fish penalty cannot exceed number of fish caught"

    # Average weight check (reasonable range)
    if num_fish > 0:
        avg_weight = total_weight / num_fish
        if avg_weight > MAX_AVG_FISH_WEIGHT:
            return (
                False,
                f"Average fish weight exceeds reasonable maximum ({MAX_AVG_FISH_WEIGHT} lbs)",
            )

        if avg_weight < MIN_AVG_FISH_WEIGHT and total_weight > 0:
            return (
                False,
                f"Average fish weight below reasonable minimum ({MIN_AVG_FISH_WEIGHT} lbs)",
            )

    return True, None


def sanitize_weight(value: str) -> Decimal:
    """
    Sanitize and convert weight input to Decimal.

    Args:
        value: Weight value as string

    Returns:
        Decimal representation of weight

    Raises:
        ValueError: If value cannot be converted
    """
    try:
        weight = Decimal(str(value).strip())
        if weight < 0:
            raise ValueError("Weight cannot be negative")
        return weight
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid weight value: {value}") from e
