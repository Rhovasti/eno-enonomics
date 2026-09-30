"""Tests for the citystate profile parser (Phase 1)."""

from pathlib import Path

import pytest

from ..citystates.parser import (
    GROWTH_PRIOR_BY_STATE,
    SYNTHETIC_FOUNDED_CYCLE,
    CitystateSpec,
    load_citystates,
    parse_citystate,
)
from .conftest import BUNDLED_CITYSTATES_DIR


def test_parse_new_format_aira(corpus_dir: Path) -> None:
    """Aira.md (new format): founded_cycle + latitude/longitude."""
    spec = parse_citystate(corpus_dir / "Aira.md")
    assert spec.name == "Aira"
    assert spec.founded_cycle == 143
    assert spec.latitude == pytest.approx(36.24)
    assert spec.longitude == pytest.approx(28.43)
    assert spec.population == 2777
    assert spec.temporal_state == "Night"
    assert spec.growth_rate == pytest.approx(-0.007, abs=1e-4)  # -0.7%


def test_parse_old_format_aiya(corpus_dir: Path) -> None:
    """Aiya.md (old format): founded + coordinates: [lat, lon]."""
    spec = parse_citystate(corpus_dir / "Aiya.md")
    assert spec.founded_cycle == 180
    assert spec.latitude == pytest.approx(18.77)
    assert spec.longitude == pytest.approx(85.73)
    assert spec.temporal_state == "Day"
    assert spec.growth_rate == pytest.approx(0.024, abs=1e-4)  # +2.4%


def test_loads_all_citystates(corpus_specs) -> None:
    assert len(corpus_specs) == 143
    names = {s.name for s in corpus_specs}
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


def test_valsang_stub_gets_synthetic_values(corpus_dir: Path) -> None:
    """Valsang lacks founding + coords → synthetic defaults, still parseable."""
    spec = parse_citystate(corpus_dir / "Valsang.md")
    assert spec.founded_cycle > 0  # synthetic
    assert spec.population == 12783
    assert spec.temporal_state == "Dusk"


def test_growth_prior_covers_known_states() -> None:
    # Every normalized temporal_state bucket we expect has a growth prior.
    for state in ["Dawn", "Day", "Dusk", "Noon", "Night", "Drifters"]:
        assert state in GROWTH_PRIOR_BY_STATE


# --- Bundled synthetic profiles (always available, so these run in CI) ---


def test_parse_bundled_new_format() -> None:
    """New format with a glossed temporal state, wikilink valley and growth line."""
    spec = parse_citystate(BUNDLED_CITYSTATES_DIR / "Highcrag.md")
    assert spec.name == "Highcrag"
    assert spec.founded_cycle == 120
    assert (spec.latitude, spec.longitude) == (pytest.approx(41.5), pytest.approx(-12.25))
    assert spec.temporal_state == "Night"
    assert spec.valley == "Night"
    assert spec.growth_rate == pytest.approx(-0.005)
    assert spec.elevation == 900
    assert spec.tags == ["location", "city", "mountain", "mine"]


def test_parse_bundled_old_format() -> None:
    """Old format: founded + coordinates: [lat, lon], pipe-style wikilink valley."""
    spec = parse_citystate(BUNDLED_CITYSTATES_DIR / "Saltmere.md")
    assert spec.founded_cycle == 210
    assert (spec.latitude, spec.longitude) == (pytest.approx(12.75), pytest.approx(64.5))
    assert spec.valley == "Day"
    assert spec.growth_rate == pytest.approx(0.021)
    assert "port" in spec.infrastructure


def test_parse_bundled_stub_gets_synthetic_values() -> None:
    """A stub without founding or coordinates gets synthetic defaults and a prior."""
    spec = parse_citystate(BUNDLED_CITYSTATES_DIR / "Nowhereton.md")
    assert spec.founded_cycle == SYNTHETIC_FOUNDED_CYCLE
    assert (spec.latitude, spec.longitude) == (0.0, 0.0)
    assert spec.growth_rate == GROWTH_PRIOR_BY_STATE["Dusk"]


def test_load_citystates_rejects_a_missing_folder(tmp_path: Path) -> None:
    """A folder that does not exist is an error, not an empty set of profiles."""
    with pytest.raises(FileNotFoundError, match="no-such-folder"):
        load_citystates(tmp_path / "no-such-folder")


def test_load_citystates_accepts_an_empty_folder(tmp_path: Path) -> None:
    """An existing folder with no profiles loads as an empty list."""
    assert load_citystates(tmp_path) == []
