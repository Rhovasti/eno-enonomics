"""Tests for GeoJSON loading functionality."""

import pytest
from pathlib import Path
from decimal import Decimal

from ..io_geojson import GeoJSONLoader
from ..models import TechLevel


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
        "Religion": "Asta"
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
        "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}
    }
    
    operator = loader._feature_to_operator(feature, "test")
    lat, lon = operator.coord
    assert -90 <= lat <= 90
    assert -180 <= lon <= 180
    
    # Invalid coordinates (empty)
    feature_invalid = {
        "properties": {"Id": 1, "Burg": "Test"},
        "geometry": {"coordinates": []}
    }
    
    with pytest.raises(ValueError, match="Invalid coordinates"):
        loader._feature_to_operator(feature_invalid, "test")