"""Tests for the scarcity price curve."""

import itertools
from decimal import Decimal

import pytest

from ..models import SimulationConfig
from ..pricing import MAX_SUPPLY_RATIO, MIN_SUPPLY_RATIO, PriceCalculator
from ..taxonomy import create_default_taxonomy

BALANCED_REGION = Decimal(1)


def _multiplier(ratio: str, elasticity: str = "1.5") -> Decimal:
    """Local scarcity multiplier for a supply/demand ratio, with a balanced region."""
    config = SimulationConfig(price_elasticity=Decimal(elasticity))
    calc = PriceCalculator(create_default_taxonomy(), config)
    return calc._apply_scarcity_adjustment(Decimal(1), Decimal(ratio), Decimal(1), BALANCED_REGION)


def test_balanced_market_keeps_base_price() -> None:
    """Supply equal to demand leaves the base price unchanged."""
    assert _multiplier("1") == Decimal(1)


def test_price_falls_monotonically_as_supply_rises() -> None:
    """More local supply never raises the price (no step discontinuities)."""
    ratios = [f"{r / 100:.2f}" for r in range(1, 300, 3)]
    prices = [_multiplier(r) for r in ratios]

    assert all(later <= earlier for earlier, later in itertools.pairwise(prices))


def test_curve_is_continuous_at_former_thresholds() -> None:
    """The old step function jumped at 0.5, 0.8 and 2.0; the new curve does not."""
    for threshold in ("0.5", "0.8", "2.0"):
        below = _multiplier(str(Decimal(threshold) - Decimal("0.001")))
        above = _multiplier(str(Decimal(threshold) + Decimal("0.001")))
        assert abs(below - above) < Decimal("0.01")


def test_multiplier_is_positive_and_bounded() -> None:
    """Extreme ratios stay positive and within the bounded range."""
    lowest = _multiplier("1000")
    highest = _multiplier("0")

    assert lowest > 0
    assert lowest == _multiplier(str(MAX_SUPPLY_RATIO))
    assert highest == _multiplier(str(MIN_SUPPLY_RATIO))


@pytest.mark.parametrize(("ratio", "expected"), [("0.125", "2"), ("8", "0.5")])
def test_constant_elasticity_formula(ratio: str, expected: str) -> None:
    """Multiplier is (demand/supply) ** (1/elasticity); with elasticity 3, 8x -> 2x."""
    assert _multiplier(ratio, elasticity="3") == pytest.approx(Decimal(expected))


def test_higher_elasticity_flattens_prices() -> None:
    """More elastic demand means a smaller price response to the same shortage."""
    assert _multiplier("0.2", elasticity="3") < _multiplier("0.2", elasticity="1")


def test_supply_without_local_demand_is_cheapest() -> None:
    """An operator that produces a good nobody locally demands prices it at the floor."""
    config = SimulationConfig()
    calc = PriceCalculator(create_default_taxonomy(), config)

    price = calc._apply_scarcity_adjustment(Decimal(1), Decimal(5), Decimal(0), BALANCED_REGION)

    assert price == _multiplier(str(MAX_SUPPLY_RATIO))
