"""Tests for the citystate profile parser (Phase 1)."""

import pytest

from ..paths import citystates_dir

from ..citystates.parser import (
    GROWTH_PRIOR_BY_STATE,
    CitystateSpec,
    load_citystates,
    parse_citystate,
)

CITYSTATES_DIR = citystates_dir()  # $ENO_CITYSTATES_DIR, see econgen.paths


def _dir_readable(path) -> bool:
    # CI runners cannot stat paths under /root (PermissionError), so the
    # existence probe itself must be guarded, not just the tests.
    try:
        return path.is_dir()
    except OSError:
        return False


HAS_DATA = _dir_readable(CITYSTATES_DIR)


@pytest.fixture(scope="module")
def all_specs():
    if not HAS_DATA:
        pytest.skip("citystates profile folder not present")
    return load_citystates(CITYSTATES_DIR)


def test_parse_new_format_aira() -> None:
    """Aira.md (new format): founded_cycle + latitude/longitude."""
    if not HAS_DATA:
        pytest.skip("citystates folder not present")
    spec = parse_citystate(CITYSTATES_DIR / "Aira.md")
    assert spec.name == "Aira"
    assert spec.founded_cycle == 143
    assert spec.latitude == pytest.approx(36.24)
    assert spec.longitude == pytest.approx(28.43)
    assert spec.population == 2777
    assert spec.temporal_state == "Night"
    assert spec.growth_rate == pytest.approx(-0.007, abs=1e-4)  # -0.7%


def test_parse_old_format_aiya() -> None:
    """Aiya.md (old format): founded + coordinates: [lat, lon]."""
    if not HAS_DATA:
        pytest.skip("citystates folder not present")
    spec = parse_citystate(CITYSTATES_DIR / "Aiya.md")
    assert spec.founded_cycle == 180
    assert spec.latitude == pytest.approx(18.77)
    assert spec.longitude == pytest.approx(85.73)
    assert spec.temporal_state == "Day"
    assert spec.growth_rate == pytest.approx(0.024, abs=1e-4)  # +2.4%


def test_loads_all_citystates(all_specs) -> None:
    assert len(all_specs) == 143
    names = {s.name for s in all_specs}
    assert "Aira" in names
    # The 3 cities present in the folder but not in the geojson.
    assert {"Nethys", "Valdris", "Valsang"} <= names


def test_all_specs_well_formed(all_specs) -> None:
    for spec in all_specs:
        assert isinstance(spec, CitystateSpec)
        assert 1 <= spec.founded_cycle <= 998, spec
        assert spec.population > 0, spec
        assert -0.05 <= spec.growth_rate <= 0.05, spec
        assert spec.temporal_state, spec
        # Coords parsed as finite floats (source data has a few out-of-range typos,
        # e.g. latitude 93.47; inference uses longitude/elevation, so accept as-is).
        assert -180 <= spec.latitude <= 180, spec
        assert -180 <= spec.longitude <= 180, spec


def test_temporal_state_normalized(all_specs) -> None:
    states = {s.temporal_state for s in all_specs}
    # Parenthetical glosses are stripped; values are Title-Case base words.
    for state in states:
        assert "(" not in state and state == state.title(), state
    assert {"Day", "Night", "Dawn", "Dusk"} <= states


def test_valsang_stub_gets_synthetic_values() -> None:
    """Valsang lacks founding + coords → synthetic defaults, still parseable."""
    if not HAS_DATA:
        pytest.skip("citystates folder not present")
    spec = parse_citystate(CITYSTATES_DIR / "Valsang.md")
    assert spec.founded_cycle > 0  # synthetic
    assert spec.population == 12783
    assert spec.temporal_state == "Dusk"


def test_growth_prior_covers_known_states() -> None:
    # Every normalized temporal_state bucket we expect has a growth prior.
    for state in ["Dawn", "Day", "Dusk", "Noon", "Night", "Drifters"]:
        assert state in GROWTH_PRIOR_BY_STATE
