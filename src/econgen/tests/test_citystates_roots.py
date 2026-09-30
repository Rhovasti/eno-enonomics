"""Tests for citystate Root (founding origin) assignment."""

from ..citystates.parser import CitystateSpec
from ..citystates.roots import assign_root


def _spec(**overrides: object) -> CitystateSpec:
    fields: dict = {
        "name": "Plainsville",
        "founded_cycle": 100,
        "population": 5000,
        "growth_rate": 0.01,
        "temporal_state": "Unknown",
        "valley": "Unknown",
        "latitude": 0.0,
        "longitude": 0.0,
    }
    fields.update(overrides)
    return CitystateSpec(**fields)


def test_city_without_signals_gets_default_root() -> None:
    """No matching infrastructure, tags or state -> the Agricultural Settlement default."""
    assert assign_root(_spec()) == "Agricultural Settlement"


def test_matching_signals_still_win() -> None:
    """A city with dam/hydraulic tags is still a Hydraulic Settlement."""
    spec = _spec(tags=["dam", "hydraulic"], infrastructure=["river access"])

    assert assign_root(spec) == "Hydraulic Settlement"
