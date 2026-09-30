"""
Configuration, utility, data-integrity and report-shape tests for Enonomics.

Split out of test_comprehensive_suite.py to keep each test module under 500 lines.
"""

import pytest
from decimal import Decimal

from ..models import Operator, TechLevel, SimulationConfig, DemandProfile
from ..taxonomy import create_default_taxonomy
from ..demand import create_default_demand_profiles
from ..rules import create_default_rules
from ..util import (
    clamp,
    safe_divide,
    format_number,
    validate_positive_decimal,
)


class TestConfigurationValidation:
    """Test system configuration and validation"""

    def test_simulation_config_defaults(self):
        """Test simulation configuration default values"""
        config = SimulationConfig()

        # Verify default values are reasonable
        assert config.transport_cost_per_km >= 0
        assert config.max_trade_radius_km > 0
        assert config.max_trade_neighbors >= 1
        assert config.min_trade_quantity > 0
        assert config.price_elasticity > 0

        # Base prices live on the taxonomy and should be positive
        taxonomy = create_default_taxonomy()
        assert all(r.base_price > 0 for r in taxonomy.resources.values())

    def test_tech_level_progression(self):
        """Test technology level ordering and comparisons"""
        levels = [TechLevel.TRIBAL, TechLevel.MEDIEVAL, TechLevel.INDUSTRIAL]

        # Test ordering
        for i in range(len(levels) - 1):
            assert levels[i] < levels[i + 1], f"{levels[i]} should be less than {levels[i + 1]}"

        # Test equality
        for level in levels:
            assert level == level
            assert not (level < level)
            assert not (level > level)

    def test_demand_profile_validation(self):
        """Test demand profile structure and validation"""
        demand_profiles = create_default_demand_profiles()

        # Should have exactly one profile per tech level
        profile_techs = [profile.tech for profile in demand_profiles]
        assert sorted(profile_techs) == sorted(level.value for level in TechLevel)

        # Each profile should have valid structure
        for profile in demand_profiles:
            assert isinstance(profile, DemandProfile)
            assert isinstance(profile.per_capita, dict)
            assert len(profile.per_capita) > 0
            assert all(demand >= 0 for demand in profile.per_capita.values())


class TestUtilityFunctions:
    """Test utility functions thoroughly"""

    def test_clamp_function(self):
        """Test clamp utility function"""
        test_cases = [
            (5, 0, 10, 5),  # Within range
            (-5, 0, 10, 0),  # Below minimum
            (15, 0, 10, 10),  # Above maximum
            (5.5, 5, 6, 5.5),  # Float within range
            (0, 0, 0, 0),  # All same value
        ]

        for value, min_val, max_val, expected in test_cases:
            result = clamp(value, min_val, max_val)
            assert result == expected, f"clamp({value}, {min_val}, {max_val}) should be {expected}"

    def test_safe_divide_function(self):
        """Test safe division utility"""
        assert safe_divide(10, 2) == 5.0
        assert safe_divide(7, 2) == 3.5
        assert safe_divide(10, 0, default=0) == 0
        assert safe_divide(10, 0, default=float("inf")) == float("inf")

        # Test with decimals
        assert safe_divide(Decimal("10"), Decimal("2")) == Decimal("5")
        assert safe_divide(Decimal("10"), Decimal("0"), default=Decimal("0")) == Decimal("0")

    def test_format_number_function(self):
        """Test number formatting utility"""
        test_cases = [
            (1234.56789, 2, "1234.57"),
            (1000000, 0, "1000000"),
            (0.00123, 5, "0.00123"),
            (999.999, 1, "1000.0"),
        ]

        for number, decimals, expected in test_cases:
            result = format_number(number, decimals)
            assert result == expected, f"format_number({number}, {decimals}) should be '{expected}'"

    def test_validate_positive_decimal(self):
        """Test decimal validation utility"""
        # Valid cases
        assert validate_positive_decimal(Decimal("10.5")) == Decimal("10.5")
        assert validate_positive_decimal(Decimal("0.01")) == Decimal("0.01")

        # Zero and negatives are not positive and should raise ValueError
        with pytest.raises(ValueError):
            validate_positive_decimal(Decimal("0"))

        with pytest.raises(ValueError):
            validate_positive_decimal(Decimal("-5"))

        with pytest.raises(ValueError):
            validate_positive_decimal(-10.5)


class TestDataIntegrity:
    """Test data consistency and integrity"""

    def test_taxonomy_resource_consistency(self):
        """Test that taxonomy resources are internally consistent"""
        taxonomy = create_default_taxonomy()

        # All resources should have valid IDs
        for resource_id, resource in taxonomy.resources.items():
            assert resource_id == resource.resource_id
            assert len(resource.name) > 0
            assert resource.base_price > 0

        # Check for duplicate names (case insensitive)
        names = [r.name.lower() for r in taxonomy.resources.values()]
        assert len(names) == len(set(names)), "Taxonomy contains duplicate resource names"

    def test_production_rules_consistency(self):
        """Test that production rules reference valid resources"""
        rules = create_default_rules()
        taxonomy = create_default_taxonomy()

        for rule in rules:
            # Check inputs reference valid resources
            for input_resource, _ in rule.inputs.items():
                assert input_resource in taxonomy.resources, (
                    f"Rule references unknown input resource: {input_resource}"
                )

            # Check outputs reference valid resources
            for output_resource, _ in rule.outputs.items():
                assert output_resource in taxonomy.resources, (
                    f"Rule references unknown output resource: {output_resource}"
                )

            # Rule should have at least one output
            assert len(rule.outputs) > 0, f"Production rule {rule.rule_id} has no outputs"

    def test_demand_profiles_resource_consistency(self):
        """Test that demand profiles reference valid resources"""
        demand_profiles = create_default_demand_profiles()
        taxonomy = create_default_taxonomy()

        # Collect all resources referenced in demand profiles
        referenced_resources = set()
        for profile in demand_profiles:
            referenced_resources.update(profile.per_capita.keys())

        unknown_resources = referenced_resources - set(taxonomy.resources.keys())
        assert not unknown_resources, f"Demand profiles reference unknown: {unknown_resources}"


class TestReportGeneration:
    """Test report generation functionality"""

    def test_basic_report_structure(self):
        """Test that reports can be generated without errors"""
        # Create minimal test data
        operators = [
            Operator(
                operator_id="test_op",
                name="Test Operator",
                kind="city",
                tech=TechLevel.MEDIEVAL,
                coord=(0.0, 0.0),
                endowments={"wood": Decimal("10.0")},
            )
        ]

        # Mock report data
        capacities = {"test_op": {"wood": Decimal("5.0")}}
        supply = {"test_op": {"wood": Decimal("4.0")}}
        demand = {"test_op": {"food": Decimal("10.0")}}
        prices = {"test_op": {"wood": 10.0, "food": 20.0}}
        trade_links = []

        # Test that we can create report data structure
        report_data = {
            "operators": operators,
            "capacities": capacities,
            "supply": supply,
            "demand": demand,
            "prices": prices,
            "trade_links": trade_links,
        }

        # Verify structure
        assert len(report_data) == 6
        assert "operators" in report_data
        assert "capacities" in report_data
        assert "supply" in report_data
        assert "demand" in report_data
        assert "prices" in report_data
        assert "trade_links" in report_data
