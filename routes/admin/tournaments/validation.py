"""Validation helpers for tournament result entry."""

from decimal import Decimal
from typing import Optional, Tuple


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

    if total_weight > 50.0:  # Reasonable maximum for 5 bass
        return False, "Total weight exceeds reasonable maximum (50 lbs)"

    # Validate big bass weight
    if big_bass_weight < 0:
        return False, "Big bass weight cannot be negative"

    if big_bass_weight > 15.0:  # World record largemouth is ~22 lbs, but rare
        return False, "Big bass weight exceeds reasonable maximum (15 lbs)"

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
        if avg_weight > 10.0:  # Each bass over 10 lbs is suspicious
            return False, "Average fish weight exceeds reasonable maximum"

        if avg_weight < 0.5 and total_weight > 0:  # Each bass under 0.5 lbs is suspicious
            return False, "Average fish weight below reasonable minimum"

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
