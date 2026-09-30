"""Tests for citystate governance assignment (synthetic specs, no profile folder needed)."""

from ..citystates.governance import (
    assign_governance,
    assign_initial_governance,
    create_dam_settlement,
)
from ..citystates.governance_types import CATALOG
from ..citystates.parser import CitystateSpec


def _spec(index: int) -> CitystateSpec:
    """A plain synthetic citystate with no distinguishing signals."""
    return CitystateSpec(
        name=f"Town {index}",
        founded_cycle=100,
        population=5000,
        growth_rate=0.01,
        temporal_state="Noon",
        valley="Noon",
        latitude=0.0,
        longitude=float(index),
    )


def test_dam_settlement_is_oriental_despotism() -> None:
    """Valvestrum is lore-assigned Oriental Despotism despite its 'Dominion' state name."""
    (assignment,) = assign_governance([create_dam_settlement()])

    assert assignment.gov_type == "Oriental Despotism"
    assert assignment.hard_coded


def test_initial_governance_covers_every_type() -> None:
    """With enough citystates, every governance type appears at least once.

    Identical specs make every override gain equal, which previously sent every
    missing type to the same city, each override undoing the previous one.
    """
    specs = [_spec(i) for i in range(len(CATALOG) + 10)]
    roots = {spec.name: "Agricultural Settlement" for spec in specs}

    initial = assign_initial_governance(specs, roots, settled={})

    assert set(initial.values()) == {gov.name for gov in CATALOG}
