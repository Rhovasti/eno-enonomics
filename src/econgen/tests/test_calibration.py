"""Tests for capacity calibration."""

from decimal import Decimal

import pytest

from ..calibration import calibrate_capacities
from ..models import Capacity
from ..rules import RulesEngine, create_default_rules


@pytest.fixture
def rules_engine() -> RulesEngine:
    """Provide the default rules engine."""
    return RulesEngine(create_default_rules())


def _farming(operator_id: str, max_rate: str) -> Capacity:
    return Capacity(
        operator_id=operator_id, rule_id="farming", max_rate=Decimal(max_rate)
    )


def test_world_output_matches_world_demand(rules_engine: RulesEngine) -> None:
    """Calibrated farming output (3 food per unit) equals total food demand."""
    capacities = [_farming("a", "1"), _farming("b", "3")]
    demand = {"a": {"food": Decimal("60")}, "b": {"food": Decimal("60")}}

    calibrated = calibrate_capacities(capacities, rules_engine, demand)

    total_food = sum(c.max_rate * c.efficiency * Decimal("3") for c in calibrated)
    assert total_food == Decimal("120")


def test_relative_productivity_is_preserved(rules_engine: RulesEngine) -> None:
    """Calibration scales all operators of a rule by the same factor."""
    capacities = [_farming("a", "1"), _farming("b", "3")]
    demand = {"a": {"food": Decimal("90")}}

    calibrated = calibrate_capacities(capacities, rules_engine, demand)

    assert calibrated[1].max_rate / calibrated[0].max_rate == Decimal("3")


def test_supply_demand_ratio_scales_target(rules_engine: RulesEngine) -> None:
    """A ratio of 1.5 targets 50% more world supply than demand."""
    capacities = [_farming("a", "2")]
    demand = {"a": {"food": Decimal("60")}}

    calibrated = calibrate_capacities(capacities, rules_engine, demand, Decimal("1.5"))

    assert calibrated[0].max_rate * Decimal("3") == Decimal("90")


def test_rule_without_demand_is_unscaled(rules_engine: RulesEngine) -> None:
    """Rules whose output nobody demands keep their raw capacity."""
    capacities = [_farming("a", "2")]

    calibrated = calibrate_capacities(
        capacities, rules_engine, {"a": {"tools": Decimal("5")}}
    )

    assert calibrated[0].max_rate == Decimal("2")
