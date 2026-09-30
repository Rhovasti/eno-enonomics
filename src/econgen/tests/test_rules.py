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
    "forestry",
    "mining_potential",
]

TRIBAL_RULES = {
    "farming",
    "fishing",
    "toolmaking",
    "forestry",
    "quarrying",
    "seed-cultivation",
    "fiber-farming",
    # Universal (endowment-free) fantastical gathering rule
    "dust-collection",
}
MEDIEVAL_RULES = TRIBAL_RULES | {
    "weaving",
    "jewelry-crafting",
    "iron-mining",
    "coal-mining",
    "precious-metal-mining",
    "gem-mining",
}
INDUSTRIAL_RULES = MEDIEVAL_RULES | {
    "steel-making",
    "machinery-production",
    "industrial-iron-mining",
    "industrial-coal-mining",
}


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
        (TechLevel.TRIBAL, TRIBAL_RULES),
        (TechLevel.MEDIEVAL, MEDIEVAL_RULES),
        (TechLevel.INDUSTRIAL, INDUSTRIAL_RULES),
    ],
)
def test_eligible_rules_follow_tech_order(tech: TechLevel, expected_rules: set[str]) -> None:
    """Rules unlock by tech order (tribal < medieval < industrial), not alphabetically."""
    engine = RulesEngine(create_default_rules())

    eligible = {rule.rule_id for rule in engine.get_eligible_rules(_operator(tech))}

    assert eligible == expected_rules


def test_get_rules_by_tech_includes_lower_tiers() -> None:
    """Industrial tech level includes every default rule."""
    engine = RulesEngine(create_default_rules())

    assert len(engine.get_rules_by_tech(TechLevel.INDUSTRIAL)) == len(create_default_rules())
    # Tech-only view (no endowment filter): the tribal-tier fantastical rules
    # count here even though sap-tapping is endowment-gated for eligibility.
    tribal_tech_rules = TRIBAL_RULES | {"sap-tapping"}
    assert {r.rule_id for r in engine.get_rules_by_tech(TechLevel.TRIBAL)} == tribal_tech_rules


def test_every_rule_input_has_a_producer() -> None:
    """Each resource consumed by a default rule is produced by some default rule."""
    rules = create_default_rules()
    produced = {resource for rule in rules for resource in rule.outputs}
    consumed = {resource for rule in rules for resource in rule.inputs}

    assert consumed - produced == set()
