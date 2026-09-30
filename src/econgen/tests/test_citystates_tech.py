"""Tech level must be consistent across citystate economy, profile and simulator."""

import pytest

from ..citystates.economy import make_economy, spec_to_operator
from ..citystates.parser import CitystateSpec
from ..citystates.profiles import ProfileConfig, compute_citystate_profile
from ..citystates.simulator import _tech_rank
from ..models import TECH_ORDER


def _spec(temporal_state: str, tags: list) -> CitystateSpec:
    return CitystateSpec(
        name="Testburg",
        founded_cycle=100,
        population=5000,
        growth_rate=0.01,
        temporal_state=temporal_state,
        valley="Noon",
        latitude=0.0,
        longitude=0.0,
        tags=tags,
    )


@pytest.mark.parametrize(
    ("temporal_state", "tags", "expected"),
    [
        ("Noon", ["industrial"], "industrial"),
        ("Autotrophic Founder", [], "medieval"),
        ("Night", [], "tribal"),
    ],
)
def test_profile_and_simulator_use_the_economy_tech(
    temporal_state: str, tags: list, expected: str
) -> None:
    """Profile label and simulator start rank match the tech used for supply/demand."""
    spec = _spec(temporal_state, tags)
    taxonomy, _, _ = make_economy()
    economy_tech = str(spec_to_operator(spec).tech)

    profile = compute_citystate_profile(spec, {}, {}, {}, taxonomy, ProfileConfig())

    assert economy_tech == expected
    assert profile.tech == economy_tech
    assert _tech_rank(spec) == TECH_ORDER[economy_tech]
