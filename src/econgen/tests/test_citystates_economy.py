"""Tests for citystate supply, including resources unlocked by tech progression."""

from decimal import Decimal

from ..citystates.economy import make_economy, potential_supply_for_operator, supply_for_operator
from ..models import Operator, TechLevel


def _tribal_operator() -> Operator:
    """A tribal city whose endowments would support medieval and industrial rules."""
    drivers = ["agriculture", "craftsmanship", "general_labor", "industrial_capacity"]
    return Operator(
        operator_id="Riverhold",
        name="Riverhold",
        kind="city",
        tech=TechLevel.TRIBAL,
        coord=(0.0, 0.0),
        population=5000,
        endowments={driver: Decimal("0.5") for driver in drivers},
    )


def test_current_resources_are_unchanged() -> None:
    """Resources the city already produces keep exactly their current rates."""
    _, rules_engine, _ = make_economy()
    operator = _tribal_operator()
    current = supply_for_operator(operator, rules_engine)

    potential, _ = potential_supply_for_operator(operator, rules_engine)

    assert {r: potential[r] for r in current} == current


def test_higher_tier_resources_unlock_at_their_tech_rank() -> None:
    """Resources out of reach at the current tech are added with their unlock rank."""
    _, rules_engine, _ = make_economy()
    operator = _tribal_operator()
    current = supply_for_operator(operator, rules_engine)

    potential, unlock_rank = potential_supply_for_operator(operator, rules_engine)

    assert "textiles" not in current and potential["textiles"] > 0
    assert unlock_rank["textiles"] == 1  # weaving is medieval
    assert "steel" not in current and potential["steel"] > 0
    assert unlock_rank["steel"] == 2  # steel-making is industrial
    assert not set(unlock_rank) & set(current)
