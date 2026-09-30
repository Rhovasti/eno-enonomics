"""Tests for citystate endowment inference (Phase 1)."""

from pathlib import Path

import pytest

from ..citystates.endowments import infer_endowments
from ..citystates.parser import load_citystates

CITYSTATES_DIR = Path("/root/Eno/Eno-Worldbuilder2/citystates for economic profiles")
HAS_DATA = CITYSTATES_DIR.is_dir()

UNIVERSAL_DRIVERS = {
    "agriculture",
    "craftsmanship",
    "general_labor",
    "skilled_labor",
    "forestry",
    "industrial_capacity",
}


@pytest.fixture(scope="module")
def all_specs():
    if not HAS_DATA:
        pytest.skip("citystates profile folder not present")
    return load_citystates(CITYSTATES_DIR)


def test_universal_basics_present(all_specs) -> None:
    for spec in all_specs:
        endowments = infer_endowments(spec)
        for driver in UNIVERSAL_DRIVERS:
            assert driver in endowments, (spec.name, driver)
            assert endowments[driver] > 0


def test_dark_vs_sun_side_exclusive(all_specs) -> None:
    for spec in all_specs:
        endowments = infer_endowments(spec)
        has_rime = "rime_collection" in endowments
        has_ash = "ash_pilgrimage" in endowments
        # Exactly one of rime/ash (longitude is either <0 or >=0).
        assert has_rime ^ has_ash, spec.name
        if spec.longitude < 0:
            assert has_rime
        else:
            assert has_ash


def test_mining_yields_element_deposits(all_specs) -> None:
    mining_city = next(s for s in all_specs if s.elevation and s.elevation > 500)
    endowments = infer_endowments(mining_city)
    assert endowments.get("mining_potential", 0) > 0
    element_deposits = [k for k in endowments if k.endswith("_deposit") and k != "mold_deposit"]
    assert 1 <= len(element_deposits) <= 2, (mining_city.name, element_deposits)


def test_inference_is_deterministic(all_specs) -> None:
    for spec in all_specs[:10]:
        assert infer_endowments(spec) == infer_endowments(spec)


def test_coastal_city_gets_fishing_and_pitch(all_specs) -> None:
    coastal = next(
        (
            s
            for s in all_specs
            if "port" in s.tags or "coastal" in s.tags or "port" in s.infrastructure
        ),
        None,
    )
    if coastal is None:
        pytest.skip("no coastal city in fixture")
    endowments = infer_endowments(coastal)
    assert "fishing" in endowments and "trade_access" in endowments
    assert "pitch_depth" in endowments
