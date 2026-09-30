"""Tests for Pydantic models."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from ..models import (
    Capacity,
    DemandProfile,
    Operator,
    ProductionRule,
    Resource,
    SimulationConfig,
    TechLevel,
    TradeLink,
)


def test_tech_level_comparisons():
    """Test technology level comparison operators."""
    assert TechLevel.TRIBAL < TechLevel.MEDIEVAL
    assert TechLevel.MEDIEVAL < TechLevel.INDUSTRIAL
    assert TechLevel.INDUSTRIAL > TechLevel.TRIBAL
    assert TechLevel.MEDIEVAL >= TechLevel.TRIBAL
    assert TechLevel.MEDIEVAL <= TechLevel.INDUSTRIAL


def test_resource_validation():
    """Test resource model validation."""
    # Valid resource
    resource = Resource(
        resource_id="test-wood",
        name="Test Wood",
        tier=0,
        tech_min=TechLevel.TRIBAL,
        base_price=Decimal("1.5"),
    )
    assert resource.resource_id == "test-wood"
    assert resource.tier == 0
    assert resource.tech_min == TechLevel.TRIBAL

    # Invalid resource ID (uppercase)
    with pytest.raises(ValidationError):
        Resource(
            resource_id="Test-Wood",  # Should be lowercase
            name="Test Wood",
            tier=0,
            tech_min=TechLevel.TRIBAL,
            base_price=Decimal("1.5"),
        )

    # Invalid tier
    with pytest.raises(ValidationError):
        Resource(
            resource_id="test-wood",
            name="Test Wood",
            tier=5,  # Should be 0-3
            tech_min=TechLevel.TRIBAL,
            base_price=Decimal("1.5"),
        )

    # Invalid price
    with pytest.raises(ValidationError):
        Resource(
            resource_id="test-wood",
            name="Test Wood",
            tier=0,
            tech_min=TechLevel.TRIBAL,
            base_price=Decimal(0),  # Should be > 0
        )


def test_production_rule_validation():
    """Test production rule model validation."""
    # Valid rule
    rule = ProductionRule(
        rule_id="test-toolmaking",
        name="Test Toolmaking",
        inputs={"wood": Decimal("2.0"), "stone": Decimal("1.0")},
        outputs={"tools": Decimal("1.0")},
        tech_min=TechLevel.TRIBAL,
    )
    assert len(rule.inputs) == 2
    assert len(rule.outputs) == 1
    assert rule.tech_min == TechLevel.TRIBAL

    # Empty inputs should be allowed (resource extraction)
    extraction_rule = ProductionRule(
        rule_id="test-extraction",
        name="Test Extraction",
        inputs={},  # Empty inputs OK for extraction
        outputs={"wood": Decimal("2.0")},
        tech_min=TechLevel.TRIBAL,
    )
    assert len(extraction_rule.inputs) == 0
    assert len(extraction_rule.outputs) == 1

    # Empty outputs should fail
    with pytest.raises(ValidationError):
        ProductionRule(
            rule_id="test-rule",
            name="Test Rule",
            inputs={"input": Decimal("1.0")},
            outputs={},  # Should have at least one output
            tech_min=TechLevel.TRIBAL,
        )

    # Zero quantity should fail
    with pytest.raises(ValidationError):
        ProductionRule(
            rule_id="test-rule",
            name="Test Rule",
            inputs={"input": Decimal(0)},  # Should be > 0
            outputs={"output": Decimal("1.0")},
            tech_min=TechLevel.TRIBAL,
        )


def test_operator_validation():
    """Test operator model validation."""
    # Valid operator
    operator = Operator(
        operator_id="test-city-1",
        name="Test City",
        kind="city",
        tech=TechLevel.MEDIEVAL,
        coord=(45.0, -120.0),
        population=10000,
    )
    assert operator.coord == (45.0, -120.0)
    assert operator.population == 10000

    # Invalid coordinates
    with pytest.raises(ValidationError):
        Operator(
            operator_id="test-city-1",
            name="Test City",
            kind="city",
            tech=TechLevel.MEDIEVAL,
            coord=(95.0, -120.0),  # Latitude > 90
            population=10000,
        )

    with pytest.raises(ValidationError):
        Operator(
            operator_id="test-city-1",
            name="Test City",
            kind="city",
            tech=TechLevel.MEDIEVAL,
            coord=(45.0, -185.0),  # Longitude < -180
            population=10000,
        )


def test_capacity_model():
    """Test capacity model."""
    capacity = Capacity(
        operator_id="test-op",
        rule_id="test-rule",
        max_rate=Decimal("5.5"),
        efficiency=Decimal("1.2"),
    )
    assert capacity.max_rate == Decimal("5.5")
    assert capacity.efficiency == Decimal("1.2")

    # Invalid max_rate
    with pytest.raises(ValidationError):
        Capacity(
            operator_id="test-op",
            rule_id="test-rule",
            max_rate=Decimal(0),  # Should be > 0
            efficiency=Decimal("1.0"),
        )

    # Invalid efficiency
    with pytest.raises(ValidationError):
        Capacity(
            operator_id="test-op",
            rule_id="test-rule",
            max_rate=Decimal("5.0"),
            efficiency=Decimal("3.0"),  # Should be <= 2.0
        )


def test_trade_link_model():
    """Test trade link model."""
    trade_link = TradeLink(
        source_id="city-a",
        dest_id="city-b",
        resource_id="tools",
        quantity=Decimal("10.0"),
        distance_km=Decimal("50.0"),
        transport_cost=Decimal("1.0"),
        price_source=Decimal("5.0"),
        price_dest=Decimal("7.0"),
        profit_margin=Decimal("1.0"),
    )

    # Test profitability calculation
    assert trade_link.is_profitable

    # Test unprofitable trade
    unprofitable = TradeLink(
        source_id="city-a",
        dest_id="city-b",
        resource_id="tools",
        quantity=Decimal("10.0"),
        distance_km=Decimal("50.0"),
        transport_cost=Decimal("5.0"),
        price_source=Decimal("7.0"),
        price_dest=Decimal("6.0"),  # Lower than source + transport
        profit_margin=Decimal("-6.0"),
    )
    assert not unprofitable.is_profitable


def test_simulation_config():
    """Test simulation configuration model."""
    # Default config
    config = SimulationConfig()
    assert config.max_trade_neighbors == 8
    assert config.max_trade_radius_km == Decimal(800)
    assert config.strict_validation

    # Custom config
    custom_config = SimulationConfig(
        max_trade_neighbors=12, max_trade_radius_km=Decimal(1200), seed=42
    )
    assert custom_config.max_trade_neighbors == 12
    assert custom_config.seed == 42


def test_demand_profile_model():
    """Test demand profile model."""
    profile = DemandProfile(
        tech=TechLevel.MEDIEVAL,
        per_capita={"food": Decimal("2.0"), "tools": Decimal("0.5"), "weapons": Decimal("0.2")},
    )
    assert profile.tech == TechLevel.MEDIEVAL
    assert len(profile.per_capita) == 3
    assert profile.per_capita["food"] == Decimal("2.0")
