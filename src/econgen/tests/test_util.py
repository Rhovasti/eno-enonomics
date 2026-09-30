"""Tests for utility functions."""

from decimal import Decimal

import pytest

from ..util import (
    calculate_great_circle_distance,
    clamp,
    deduplicate_list_preserve_order,
    format_number,
    get_deterministic_sample,
    normalize_resource_id,
    safe_divide,
    set_seed,
    validate_positive_decimal,
)


def test_set_seed():
    """Test random seed setting."""
    import random

    import numpy as np

    # Test with seed
    set_seed(42)
    r1 = random.random()
    n1 = np.random.random()

    set_seed(42)  # Reset with same seed
    r2 = random.random()
    n2 = np.random.random()

    assert r1 == r2  # Should be identical with same seed
    assert n1 == n2

    # Test with None (should not crash)
    set_seed(None)


def test_calculate_great_circle_distance():
    """Test distance calculation between coordinates."""
    # Distance between known cities (approx)
    seattle = (47.6062, -122.3321)
    portland = (45.5152, -122.6784)

    distance = calculate_great_circle_distance(seattle, portland)
    assert 220 <= distance <= 250  # Should be ~234 km based on actual calculation

    # Same point should have zero distance
    distance_same = calculate_great_circle_distance(seattle, seattle)
    assert distance_same == Decimal("0.0")

    # Test invalid coordinates
    with pytest.raises(ValueError):
        calculate_great_circle_distance((95.0, 0.0), (0.0, 0.0))  # Invalid lat

    with pytest.raises(ValueError):
        calculate_great_circle_distance((0.0, 185.0), (0.0, 0.0))  # Invalid lon


def test_normalize_resource_id():
    """Test resource ID normalization."""
    assert normalize_resource_id("Iron Ore") == "iron-ore"
    assert normalize_resource_id("PRECIOUS_METALS") == "precious-metals"
    assert normalize_resource_id("  Mixed Case  ") == "mixed-case"
    assert normalize_resource_id("already-normalized") == "already-normalized"


def test_clamp():
    """Test value clamping."""
    assert clamp(Decimal(5), Decimal(1), Decimal(10)) == Decimal(5)
    assert clamp(Decimal(0), Decimal(1), Decimal(10)) == Decimal(1)
    assert clamp(Decimal(15), Decimal(1), Decimal(10)) == Decimal(10)


def test_safe_divide():
    """Test safe division with default values."""
    assert safe_divide(Decimal(10), Decimal(2)) == Decimal(5)
    assert safe_divide(Decimal(10), Decimal(0)) == Decimal(0)  # Default
    assert safe_divide(Decimal(10), Decimal(0), Decimal(99)) == Decimal(99)


def test_format_number():
    """Test number formatting."""
    assert format_number(Decimal("123.456"), 2) == "123.46"
    assert format_number(Decimal("123.456"), 1) == "123.5"
    assert format_number(Decimal("123.456"), 0) == "123"
    assert format_number(Decimal("0.001"), 3) == "0.001"


def test_deduplicate_list_preserve_order():
    """Test list deduplication while preserving order."""
    input_list = [1, 2, 3, 2, 4, 1, 5]
    result = deduplicate_list_preserve_order(input_list)
    assert result == [1, 2, 3, 4, 5]

    # Test with strings
    string_list = ["a", "b", "c", "b", "a"]
    result_str = deduplicate_list_preserve_order(string_list)
    assert result_str == ["a", "b", "c"]

    # Test empty list
    assert deduplicate_list_preserve_order([]) == []


def test_validate_positive_decimal():
    """Test positive decimal validation."""
    # Valid positive value
    assert validate_positive_decimal(Decimal("5.5")) == Decimal("5.5")

    # Invalid zero
    with pytest.raises(ValueError, match="must be positive"):
        validate_positive_decimal(Decimal(0))

    # Invalid negative
    with pytest.raises(ValueError, match="must be positive"):
        validate_positive_decimal(Decimal("-1.5"))

    # Custom field name in error
    with pytest.raises(ValueError, match="price must be positive"):
        validate_positive_decimal(Decimal(0), "price")


def test_get_deterministic_sample():
    """Test deterministic sampling."""
    items = list(range(100))

    # Set seed for consistent testing
    set_seed(42)

    # Test normal sampling
    sample1 = get_deterministic_sample(items, 5)

    # Reset to same seed
    set_seed(42)
    sample2 = get_deterministic_sample(items, 5)

    assert len(sample1) == 5
    assert sample1 == sample2  # Should be deterministic with same seed

    # Test with seed suffix
    sample_a = get_deterministic_sample(items, 5, "suffix_a")
    sample_b = get_deterministic_sample(items, 5, "suffix_b")
    assert len(sample_a) == 5
    assert len(sample_b) == 5
    assert sample_a != sample_b  # Different suffixes should give different results

    # Test with more items requested than available
    small_list = [1, 2, 3]
    sample_large = get_deterministic_sample(small_list, 10)
    assert len(sample_large) == 3  # Should return all available items

    # Test empty list
    assert get_deterministic_sample([], 5) == []
