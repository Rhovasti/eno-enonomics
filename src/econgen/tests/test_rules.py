"""Tests for production rule eligibility."""

from decimal import Decimal

import pytest

from ..models import Operator, TechLevel
from ..rules import RulesEngine, create_default_rules

ALL_DRIVERS = [
    "agriculture",
    "fishing",
    "craftsmanship",
    "general_labor",
    "industrial_capacity",
    "skilled_labor",
]


def _operator(tech: TechLevel) -> Operator:
    """Build an operator that holds every capacity driver endowment."""
    return Operator(
        operator_id=f"op-{tech.value}",
        name=f"Op {tech.value}",
        kind="city",
        tech=tech,
        coord=(0.0, 0.0),
        population=5000,
        endowments={driver: Decimal("1.0") for driver in ALL_DRIVERS},
    )


@pytest.mark.parametrize(
    ("tech", "expected_rules"),
    [
        (TechLevel.TRIBAL, {"farming", "fishing", "toolmaking"}),
        (
            TechLevel.MEDIEVAL,
            {"farming", "fishing", "toolmaking", "weaving", "jewelry-crafting"},
        ),
        (
            TechLevel.INDUSTRIAL,
            {
                "farming",
                "fishing",
                "toolmaking",
                "weaving",
                "jewelry-crafting",
                "steel-making",
                "machinery-production",
            },
        ),
    ],
)
def test_eligible_rules_follow_tech_order(
    tech: TechLevel, expected_rules: set[str]
) -> None:
    """Rules unlock by tech order (tribal < medieval < industrial), not alphabetically."""
    engine = RulesEngine(create_default_rules())

    eligible = {rule.rule_id for rule in engine.get_eligible_rules(_operator(tech))}

    assert eligible == expected_rules


def test_get_rules_by_tech_includes_lower_tiers() -> None:
    """Industrial tech level includes every default rule."""
    engine = RulesEngine(create_default_rules())

    assert len(engine.get_rules_by_tech(TechLevel.INDUSTRIAL)) == len(
        create_default_rules()
    )
    assert {r.rule_id for r in engine.get_rules_by_tech(TechLevel.TRIBAL)} == {
        "farming",
        "fishing",
        "toolmaking",
    }
