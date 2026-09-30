"""Regression tests for tech-level eligibility gating.

Previously ``operator.tech < rule.tech_min`` was lexicographic (tech values are
strings under ``use_enum_values=True``), so alphabetically ``"medieval" < "tribal"``
— medieval/industrial cities were wrongly blocked from tribal rules (farming,
toolmaking) and industrial rules were wrongly unlocked for medieval cities.
"""

from decimal import Decimal

from ..models import Operator, TechLevel
from ..rules import RulesEngine, create_default_rules


def _operator(tech: TechLevel) -> Operator:
    # All capacity drivers present, so eligibility is gated only by tech level.
    return Operator(
        operator_id="t",
        name="T",
        kind="city",
        tech=tech,
        coord=(0.0, 0.0),
        population=10000,
        endowments={
            "agriculture": Decimal(1),
            "fishing": Decimal(1),
            "craftsmanship": Decimal(1),
            "general_labor": Decimal(1),
            "skilled_labor": Decimal(1),
            "industrial_capacity": Decimal(1),
        },
    )


def _eligible_rule_ids(tech: TechLevel) -> set:
    engine = RulesEngine(create_default_rules())
    return {r.rule_id for r in engine.get_eligible_rules(_operator(tech))}


def test_medieval_operator_is_eligible_for_tribal_rules() -> None:
    eligible = _eligible_rule_ids(TechLevel.MEDIEVAL)
    assert "farming" in eligible  # tribal rule, was wrongly skipped
    assert "toolmaking" in eligible


def test_medieval_operator_is_not_eligible_for_industrial_rules() -> None:
    eligible = _eligible_rule_ids(TechLevel.MEDIEVAL)
    assert "steel-making" not in eligible  # industrial, was wrongly unlocked
    assert "machinery-production" not in eligible


def test_industrial_operator_eligible_across_all_tiers() -> None:
    eligible = _eligible_rule_ids(TechLevel.INDUSTRIAL)
    assert "farming" in eligible
    assert "jewelry-crafting" in eligible
    assert "steel-making" in eligible
