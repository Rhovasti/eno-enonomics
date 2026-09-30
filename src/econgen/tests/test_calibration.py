"""Tests for capacity calibration."""

from decimal import Decimal

import pytest

from ..calibration import (
    calculate_input_demand,
    calibrate_capacities,
    calibrate_with_input_demand,
)
from ..models import Capacity, ProductionRule, TechLevel
from ..rules import RulesEngine, create_default_rules


@pytest.fixture
def rules_engine() -> RulesEngine:
    """Provide the default rules engine."""
    return RulesEngine(create_default_rules())


def _farming(operator_id: str, max_rate: str) -> Capacity:
    return Capacity(operator_id=operator_id, rule_id="farming", max_rate=Decimal(max_rate))


def test_world_output_matches_world_demand(rules_engine: RulesEngine) -> None:
    """Calibrated farming output (3 food per unit) equals total food demand."""
    capacities = [_farming("a", "1"), _farming("b", "3")]
    demand = {"a": {"food": Decimal(60)}, "b": {"food": Decimal(60)}}

    calibrated = calibrate_capacities(capacities, rules_engine, demand)

    total_food = sum(c.max_rate * c.efficiency * Decimal(3) for c in calibrated)
    assert total_food == Decimal(120)


def test_relative_productivity_is_preserved(rules_engine: RulesEngine) -> None:
    """Calibration scales all operators of a rule by the same factor."""
    capacities = [_farming("a", "1"), _farming("b", "3")]
    demand = {"a": {"food": Decimal(90)}}

    calibrated = calibrate_capacities(capacities, rules_engine, demand)

    assert calibrated[1].max_rate / calibrated[0].max_rate == Decimal(3)


def test_supply_demand_ratio_scales_target(rules_engine: RulesEngine) -> None:
    """A ratio of 1.5 targets 50% more world supply than demand."""
    capacities = [_farming("a", "2")]
    demand = {"a": {"food": Decimal(60)}}

    calibrated = calibrate_capacities(capacities, rules_engine, demand, Decimal("1.5"))

    assert calibrated[0].max_rate * Decimal(3) == Decimal(90)


def test_rule_without_demand_is_unscaled(rules_engine: RulesEngine) -> None:
    """Rules whose output nobody demands keep their raw capacity."""
    capacities = [_farming("a", "2")]

    calibrated = calibrate_capacities(capacities, rules_engine, {"a": {"tools": Decimal(5)}})

    assert calibrated[0].max_rate == Decimal(2)


def test_input_demand_scales_with_production(rules_engine: RulesEngine) -> None:
    """Toolmaking consumes 2 wood and 1 stone per unit produced."""
    capacities = [Capacity(operator_id="smith", rule_id="toolmaking", max_rate=Decimal(5))]

    input_demand = calculate_input_demand(capacities, rules_engine)

    assert input_demand == {"smith": {"wood": Decimal(10), "stone": Decimal(5)}}


def test_rules_without_inputs_add_no_demand(rules_engine: RulesEngine) -> None:
    """Extraction rules such as forestry consume nothing."""
    capacities = [Capacity(operator_id="camp", rule_id="forestry", max_rate=Decimal(5))]

    assert calculate_input_demand(capacities, rules_engine) == {}


def test_calibration_covers_input_demand(rules_engine: RulesEngine) -> None:
    """World wood output covers final wood demand plus wood used for tools."""
    capacities = [
        Capacity(operator_id="smith", rule_id="toolmaking", max_rate=Decimal(1)),
        Capacity(operator_id="camp", rule_id="forestry", max_rate=Decimal(1)),
    ]
    final_demand = {
        "smith": {"tools": Decimal(10)},
        "camp": {"wood": Decimal(5)},
    }

    calibrated, total = calibrate_with_input_demand(capacities, rules_engine, final_demand)

    # 10 tools need 20 wood as input, on top of 5 wood of final demand
    assert total["smith"]["wood"] == Decimal(20)
    forestry = next(c for c in calibrated if c.rule_id == "forestry")
    assert forestry.max_rate * Decimal("2.5") == Decimal(25)


def test_calibration_propagates_through_production_chain(
    rules_engine: RulesEngine,
) -> None:
    """Machinery -> steel -> iron ore: each level is sized for the level above."""
    capacities = [
        Capacity(operator_id="a", rule_id=rule_id, max_rate=Decimal(1))
        for rule_id in ("machinery-production", "steel-making", "iron-mining")
    ]
    final_demand = {"a": {"machinery": Decimal(2)}}

    _, total = calibrate_with_input_demand(capacities, rules_engine, final_demand)

    # 2 machinery need 6 steel, which need 24 iron ore
    assert total["a"]["steel"] == Decimal(6)
    assert total["a"]["iron-ore"] == Decimal(24)


def test_rules_sharing_an_output_are_scaled_together() -> None:
    """Two rules producing the same resource together meet demand once, not twice."""
    rules = [
        ProductionRule(
            rule_id=rule_id,
            name=rule_id,
            tech_min=TechLevel.TRIBAL,
            inputs={},
            outputs={"food": Decimal(1)},
        )
        for rule_id in ("small-farm", "big-farm")
    ]
    engine = RulesEngine(rules)
    capacities = [
        Capacity(operator_id="a", rule_id="small-farm", max_rate=Decimal(1)),
        Capacity(operator_id="b", rule_id="big-farm", max_rate=Decimal(3)),
    ]

    calibrated = calibrate_capacities(capacities, engine, {"a": {"food": Decimal(100)}})

    assert sum(c.max_rate for c in calibrated) == Decimal(100)
    assert calibrated[1].max_rate == calibrated[0].max_rate * 3
