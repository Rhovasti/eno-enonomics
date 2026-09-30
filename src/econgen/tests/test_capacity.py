"""Tests for capacity infrastructure bonuses."""

from decimal import Decimal

from ..capacity import CapacityCalculator
from ..models import Operator, TechLevel
from ..rules import RulesEngine, create_default_rules


def _operator(walls: bool) -> Operator:
    return Operator(
        operator_id="walled" if walls else "open",
        name="Town",
        kind="city",
        tech=TechLevel.MEDIEVAL,
        coord=(0.0, 0.0),
        population=5000,
        walls=walls,
    )


def test_walls_boost_quarrying() -> None:
    """Walled towns get a 10% infrastructure bonus on stone quarrying."""
    engine = RulesEngine(create_default_rules())
    calc = CapacityCalculator(engine)
    quarrying = engine.get_rule("quarrying")

    walled = calc._calculate_infrastructure_bonus(_operator(walls=True), quarrying)
    open_town = calc._calculate_infrastructure_bonus(_operator(walls=False), quarrying)

    assert walled == open_town * Decimal("1.1")


def test_walls_do_not_boost_unrelated_rules() -> None:
    """Walls leave non-defensive rules such as farming unchanged."""
    engine = RulesEngine(create_default_rules())
    calc = CapacityCalculator(engine)
    farming = engine.get_rule("farming")

    walled = calc._calculate_infrastructure_bonus(_operator(walls=True), farming)

    assert walled == Decimal("1.0")
