"""Tests for narrative chronicles rendered from citystate dynamic histories."""

import pytest

from ..citystates.chronicles import extract_milestones, render_chronicle
from ..citystates.parser import CitystateSpec

EXTRACTIVE = {"iron-ore"}


@pytest.fixture
def spec() -> CitystateSpec:
    """A minimal citystate profile."""
    return CitystateSpec(
        name="Testhold",
        founded_cycle=900,
        population=1000,
        growth_rate=0.01,
        temporal_state="dawn",
        valley="Test",
        latitude=0.0,
        longitude=0.0,
    )


@pytest.fixture
def boom_history() -> dict:
    """A city that grows, industrialises, mines out its iron and imports on balance."""
    return {
        "name": "Testhold",
        "founded_cycle": 900,
        "time": [0, 25, 50, 98],
        "population": [1000.0, 1500.0, 2000.0, 1600.0],
        "tech": [0.5, 1.2, 2.1, 2.3],
        "resources": ["iron-ore", "food", "dust"],
        "stocks": {
            "iron-ore": [100.0, 400.0, 200.0, 40.0],
            "food": [50.0, 80.0, 120.0, 150.0],
            "dust": [0.0, 0.5, 0.2, 0.0],
        },
        "trade": {"food": [0.0, 1.0, 2.0, 3.0], "iron-ore": [0.0, -1.0, 0.0, 1.0]},
    }


@pytest.fixture
def stable_history() -> dict:
    """A city with flat population and tech, no stocks and no trade."""
    return {
        "name": "Testhold",
        "founded_cycle": 900,
        "time": [0, 49, 98],
        "population": [1000.0, 1010.0, 1000.0],
        "tech": [1.5, 1.5, 1.5],
        "resources": [],
        "stocks": {},
        "trade": {},
    }


def test_milestones_track_population_and_tech(boom_history: dict, spec: CitystateSpec) -> None:
    """Population peak and the tech-tier crossings are dated in absolute cycles."""
    m = extract_milestones(boom_history, spec, EXTRACTIVE)

    assert m["run_cycles"] == 98
    assert m["pop_ratio"] == pytest.approx(1.6)
    assert (m["pop_peak"], m["pop_peak_cycle"]) == (2000.0, 950)
    assert m["medieval_cycle"] == 925
    assert m["industrial_cycle"] == 950


def test_milestones_classify_resources(boom_history: dict, spec: CitystateSpec) -> None:
    """Resources are ordered by final stock, flagged extractive, and trivial ones dropped."""
    events = extract_milestones(boom_history, spec, EXTRACTIVE)["resource_events"]

    assert [e["resource"] for e in events] == ["food", "iron-ore"]  # dust never reaches 1
    iron = events[1]
    assert iron["extractive"] and not events[0]["extractive"]
    assert (iron["peak"], iron["peak_cycle"], iron["final"]) == (400.0, 925, 40.0)
    assert iron["depletion"] == pytest.approx(0.1)


def test_milestones_average_final_trade(boom_history: dict, spec: CitystateSpec) -> None:
    """trade_end is the mean of every resource's last trade value."""
    assert extract_milestones(boom_history, spec, EXTRACTIVE)["trade_end"] == 2.0


def test_tech_tier_held_at_founding_dates_to_founding(
    stable_history: dict, spec: CitystateSpec
) -> None:
    """A city founded medieval reached that tier at founding, and never industrialised."""
    m = extract_milestones(stable_history, spec, EXTRACTIVE)

    assert m["medieval_cycle"] == 900
    assert m["industrial_cycle"] is None


def test_chronicle_tells_a_boom_and_bust(boom_history: dict, spec: CitystateSpec) -> None:
    """The narrative covers growth, industrialisation, the mining bust and imports."""
    text = render_chronicle(boom_history, spec, EXTRACTIVE)

    assert text.startswith("# Economic Chronicle: Testhold")
    assert "founded in cycle 900 in Test Valley" in text
    assert "grew robustly from 1,000 to 1,600, peaking at 2,000 around cycle 950" in text
    assert "advanced from tribal to industrial around cycle 950" in text
    assert "reaching full industrial maturity (T=2.3)" in text
    assert "a classic extractive bust" in text
    assert "Renewable mainstays: food." in text
    assert "a net importer" in text
    assert "its mines were largely spent" in text
    assert "| iron-ore | 400 | 40 | depleted |" in text
    assert "| food | 150 | 150 | renewable |" in text


def test_chronicle_of_a_stable_city(stable_history: dict, spec: CitystateSpec) -> None:
    """A flat history reads as stable and self-sufficient, with no resource table."""
    text = render_chronicle(stable_history, spec, EXTRACTIVE)

    assert "remained roughly stable near 1,000" in text
    assert "The settlement remained medieval by cycle 998." in text
    assert "No major extractive industries defined its history." in text
    assert "broadly self-sufficient in trade" in text
    assert "a stable resource base" in text
    assert "| Resource |" not in text
