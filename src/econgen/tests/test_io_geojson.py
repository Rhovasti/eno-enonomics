"""Tests for GeoJSON loading functionality."""

import pytest
from pathlib import Path
from decimal import Decimal
from typing import Dict

from ..io_geojson import CORE_ELEMENTS, GeoJSONLoader, ensure_element_coverage
from ..models import Operator, TechLevel


def test_geojson_loader_init():
    """Test GeoJSONLoader initialization."""
    # Test strict mode
    loader_strict = GeoJSONLoader(strict=True)
    assert loader_strict.strict

    # Test non-strict mode
    loader_lenient = GeoJSONLoader(strict=False)
    assert not loader_lenient.strict


def test_load_operators_from_fixture():
    """Test loading operators from test fixture."""
    loader = GeoJSONLoader(strict=True)

    # Get path to test fixture
    fixture_path = Path(__file__).parent / "fixtures" / "tiny_world.geojson"

    operators = loader.load_operators([fixture_path])

    # Should load 3 operators from fixture
    assert len(operators) == 3

    # Check first operator (TestCity)
    test_city = next(op for op in operators if op.name == "TestCity")
    assert test_city.operator_id == "1"
    assert test_city.population == 25000
    assert test_city.tech == TechLevel.MEDIEVAL
    assert test_city.port
    assert test_city.plaza
    assert "port" in test_city.tags
    assert "market" in test_city.tags

    # Check coordinates are converted from Web Mercator
    lat, lon = test_city.coord
    assert -90 <= lat <= 90  # Valid latitude
    assert -180 <= lon <= 180  # Valid longitude

    # Check endowments
    assert "fishing" in test_city.endowments
    assert "trade_access" in test_city.endowments


def test_tech_level_inference():
    """Test technology level inference from population."""
    loader = GeoJSONLoader()

    # Test tribal inference (low pop)
    props_tribal = {"Population": 3000}
    tech = loader._infer_tech_level(props_tribal)
    assert tech == TechLevel.TRIBAL

    # Test medieval inference (medium pop)
    props_medieval = {"Population": 20000}
    tech = loader._infer_tech_level(props_medieval)
    assert tech == TechLevel.MEDIEVAL

    # Test industrial inference (high pop)
    props_industrial = {"Population": 75000}
    tech = loader._infer_tech_level(props_industrial)
    assert tech == TechLevel.INDUSTRIAL

    # Test explicit tech field override
    props_explicit = {"Population": 75000, "tech": "tribal"}
    tech = loader._infer_tech_level(props_explicit)
    assert tech == TechLevel.TRIBAL


def test_extract_tags():
    """Test tag extraction from properties."""
    loader = GeoJSONLoader()

    props = {
        "Port": "port",
        "Capital": "capital",
        "Plaza": "plaza",
        "Temple": "temple",
        "Culture": "Noon",
        "Religion": "Asta",
    }

    tags = loader._extract_tags(props)

    expected_tags = ["port", "capital", "market", "religious", "culture_noon", "religion_asta"]
    for tag in expected_tags:
        assert tag in tags


def test_extract_endowments():
    """Test endowment extraction from properties."""
    loader = GeoJSONLoader()

    # Test port endowments
    props_port = {"Port": "port", "Elevation (m)": 100}
    endowments = loader._extract_endowments(props_port)
    assert "fishing" in endowments
    assert "trade_access" in endowments
    assert endowments["fishing"] == Decimal("0.8")

    # Test elevation-based mining
    props_mountain = {"Elevation (m)": 600}
    endowments = loader._extract_endowments(props_mountain)
    assert "mining_potential" in endowments
    assert endowments["mining_potential"] == Decimal("0.6")

    # Test culture-based endowments
    props_culture = {"Culture": "Wildlands", "Population": 50000}
    endowments = loader._extract_endowments(props_culture)
    assert "forestry" in endowments
    assert "skilled_labor" in endowments


def test_file_not_found_handling():
    """Test handling of missing files."""
    loader = GeoJSONLoader(strict=False)  # Non-strict mode

    # Should not crash, just return empty list
    operators = loader.load_operators([Path("nonexistent.geojson")])
    assert len(operators) == 0

    # Strict mode should raise exception
    loader_strict = GeoJSONLoader(strict=True)
    with pytest.raises(FileNotFoundError):
        loader_strict.load_operators([Path("nonexistent.geojson")])


def test_coordinate_validation():
    """Test coordinate validation and conversion."""
    loader = GeoJSONLoader()

    # Valid feature
    feature = {
        "properties": {"Id": 1, "Burg": "Test", "Population": 1000},
        "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
    }

    operator = loader._feature_to_operator(feature, "test")
    lat, lon = operator.coord
    assert -90 <= lat <= 90
    assert -180 <= lon <= 180

    # Invalid coordinates (empty)
    feature_invalid = {"properties": {"Id": 1, "Burg": "Test"}, "geometry": {"coordinates": []}}

    with pytest.raises(ValueError, match="Invalid coordinates"):
        loader._feature_to_operator(feature_invalid, "test")


def test_basic_endowments_keep_culture_specialization():
    """Baseline endowments must not lower culture-derived specializations."""
    loader = GeoJSONLoader(strict=True)

    noon = loader._extract_endowments({"Culture": "Noon", "Population": 20000})
    night = loader._extract_endowments({"Culture": "Night", "Population": 20000})
    plain = loader._extract_endowments({"Culture": "Other", "Population": 20000})

    assert noon["agriculture"] == Decimal("0.8")
    assert night["craftsmanship"] == Decimal("0.6")
    assert plain["agriculture"] == Decimal("0.5")
    assert plain["craftsmanship"] == Decimal("0.4")


def test_industrial_capacity_uses_inferred_tech():
    """Industrial capacity follows the tech inferred from population when no tech field."""
    loader = GeoJSONLoader(strict=True)

    industrial = loader._extract_endowments({"Population": 60000})
    medieval = loader._extract_endowments({"Population": 20000})
    tribal = loader._extract_endowments({"Population": 5000})

    assert industrial["industrial_capacity"] == Decimal("0.7")
    assert medieval["industrial_capacity"] == Decimal("0.3")
    assert "industrial_capacity" not in tribal


def test_industrial_capacity_respects_explicit_tech():
    """An explicit tech field still overrides population-based inference."""
    loader = GeoJSONLoader(strict=True)

    endowments = loader._extract_endowments({"Population": 5000, "tech": "industrial"})

    assert endowments["industrial_capacity"] == Decimal("0.7")


def test_fantastical_rime_ash_split_by_longitude():
    """Dark side (lon < 0) collects Rime; sun side (lon >= 0) gets Ash pilgrimages."""
    loader = GeoJSONLoader(strict=True)

    dark: Dict[str, Decimal] = {}
    loader._infer_fantastical_endowments({"Population": 5000}, dark, "4", -50.0)
    sun: Dict[str, Decimal] = {}
    loader._infer_fantastical_endowments({"Population": 5000}, sun, "5", 50.0)

    assert dark["rime_collection"] == Decimal("0.4")
    assert "ash_pilgrimage" not in dark
    assert sun["ash_pilgrimage"] == Decimal("0.4")
    assert "rime_collection" not in sun


def _fantastical(props: dict) -> dict:
    """Endowments (base + fantastical) for one feature's properties."""
    loader = GeoJSONLoader(strict=True)
    endowments = loader._extract_endowments(props)
    loader._infer_fantastical_endowments(props, endowments, "42", 10.0)
    return endowments


def test_geography_only_cities_get_sap_and_element_deposits():
    """Without worldbuilder stocks, sap and deposits come from geographic signals."""
    farming = _fantastical({"Population": 5000, "Culture": "Noon"})
    mountain = _fantastical({"Population": 20000, "Elevation (m)": 800})

    assert "sap_harvest" in farming  # vegetation (agriculture)
    assert any(key.endswith("_deposit") for key in mountain)  # mining potential


def test_worldbuilder_stock_inference_is_unchanged():
    """With explicit stocks, sap and deposits still follow the stocks only."""
    no_ore = _fantastical({"Population": 20000, "Elevation (m)": 800, "endowments": {"stone": 50}})

    assert "sap_harvest" not in no_ore  # no wood stock
    assert not any(key.endswith("_deposit") for key in no_ore)  # no iron_ore stock


def _city(operator_id: str, tech: TechLevel, **endowments: str) -> Operator:
    return Operator(
        operator_id=operator_id,
        name=operator_id,
        kind="city",
        tech=tech,
        coord=(0.0, 0.0),
        population=10000,
        endowments={key: Decimal(value) for key, value in endowments.items()},
    )


def _elements_held(operators: list) -> set:
    return {
        key.removesuffix("_deposit")
        for op in operators
        if str(op.tech) != "tribal"
        for key in op.endowments
        if key.endswith("_deposit")
    }


def test_element_coverage_adds_missing_elements_to_mining_cities():
    """Each core element ends up minable by at least one medieval+ mining city."""
    operators = [
        _city("a", TechLevel.MEDIEVAL, mining_potential="0.6", feron_deposit="0.6"),
        _city("b", TechLevel.MEDIEVAL, mining_potential="0.3"),
        _city("hill", TechLevel.TRIBAL, mining_potential="0.9"),
        _city("plain", TechLevel.MEDIEVAL),
    ]

    ensure_element_coverage(operators)

    assert _elements_held(operators) >= set(CORE_ELEMENTS)
    assert not any(k.endswith("_deposit") for k in operators[2].endowments)  # tribal
    assert not any(k.endswith("_deposit") for k in operators[3].endowments)  # no mining
    # Fewest deposits first: "b" (0 deposits) takes cunu, the first missing element.
    assert "cunu_deposit" in operators[1].endowments


def test_element_coverage_is_a_no_op_when_all_elements_are_held():
    """Datasets that already cover every element are left unchanged."""
    operators = [
        _city(f"m{i}", TechLevel.MEDIEVAL, mining_potential="0.6", **{f"{el}_deposit": "0.6"})
        for i, el in enumerate(CORE_ELEMENTS)
    ]
    before = [dict(op.endowments) for op in operators]

    ensure_element_coverage(operators)

    assert [dict(op.endowments) for op in operators] == before
