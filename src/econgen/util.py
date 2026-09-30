"""Utility functions for determinism, distance calculations, and helpers."""

import random
import re
import numpy as np
import logging
from typing import Optional, Tuple, Union
from decimal import Decimal
from math import radians, sin, cos, sqrt, atan2

logger = logging.getLogger(__name__)


def set_seed(seed: Optional[int]) -> None:
    """Set random seed for deterministic behavior across all random number generators.

    Args:
        seed: Random seed. If None, no seeding is performed.
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        logger.info(f"Set random seed to {seed}")


def calculate_great_circle_distance(
    coord1: Tuple[float, float], coord2: Tuple[float, float]
) -> Decimal:
    """Calculate great circle distance between two coordinates using Haversine formula.

    Args:
        coord1: First coordinate (lat, lon) in degrees
        coord2: Second coordinate (lat, lon) in degrees

    Returns:
        Distance in kilometers as Decimal

    Raises:
        ValueError: If coordinates are invalid
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2

    # Validate coordinates
    if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90):
        raise ValueError(f"Invalid latitude: {lat1}, {lat2}")
    if not (-180 <= lon1 <= 180 and -180 <= lon2 <= 180):
        raise ValueError(f"Invalid longitude: {lon1}, {lon2}")

    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    # Earth radius in km
    earth_radius_km = 6371
    distance_km = earth_radius_km * c

    return Decimal(str(round(distance_km, 3)))


def normalize_resource_id(resource_id: str) -> str:
    """Normalize resource ID to lowercase with consistent formatting.

    Args:
        resource_id: Raw resource identifier

    Returns:
        Normalized resource ID: lowercase alphanumerics joined by single hyphens
    """
    return re.sub(r"[^a-z0-9]+", "-", resource_id.lower()).strip("-")


def clamp(value: Decimal, min_val: Decimal, max_val: Decimal) -> Decimal:
    """Clamp value between min and max bounds.

    Args:
        value: Value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Clamped value
    """
    return max(min_val, min(value, max_val))


def safe_divide(
    numerator: Decimal, denominator: Decimal, default: Decimal = Decimal("0")
) -> Decimal:
    """Safely divide two Decimal values, returning default if denominator is zero.

    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Value to return if denominator is zero

    Returns:
        Division result or default value
    """
    if denominator == 0:
        return default
    return numerator / denominator


def format_number(value: Union[Decimal, float, int], precision: int = 2) -> str:
    """Format Decimal number with specified precision.

    Args:
        value: Number to format
        precision: Number of decimal places

    Returns:
        Formatted number string
    """
    if precision == 0:
        return str(int(value))
    format_str = f"{{:.{precision}f}}"
    return format_str.format(float(value))


def deduplicate_list_preserve_order(items: list) -> list:
    """Remove duplicates from list while preserving order.

    Args:
        items: List with potential duplicates

    Returns:
        List with duplicates removed, order preserved
    """
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def validate_positive_decimal(value: Decimal, field_name: str = "value") -> Decimal:
    """Validate that a Decimal value is positive.

    Args:
        value: Value to validate
        field_name: Name of field for error messages

    Returns:
        Validated value

    Raises:
        ValueError: If value is not positive
    """
    if value <= 0:
        raise ValueError(f"{field_name} must be positive, got {value}")
    return value


def get_deterministic_sample(items: list, n: int, seed_suffix: str = "") -> list:
    """Get deterministic sample from list based on current random state.

    Args:
        items: Items to sample from
        n: Number of items to sample
        seed_suffix: Optional suffix to add variety while maintaining determinism

    Returns:
        Sampled items (may be fewer than n if list is smaller)
    """
    if not items:
        return []

    # Use current random state with optional suffix for variety
    if seed_suffix:
        current_state = random.getstate()
        temp_seed = hash(seed_suffix) % (2**32)
        random.seed(temp_seed)
        result = random.sample(items, min(n, len(items)))
        random.setstate(current_state)
        return result
    else:
        return random.sample(items, min(n, len(items)))


# Export key functions
__all__ = [
    "set_seed",
    "calculate_great_circle_distance",
    "normalize_resource_id",
    "clamp",
    "safe_divide",
    "format_number",
    "deduplicate_list_preserve_order",
    "validate_positive_decimal",
    "get_deterministic_sample",
]
