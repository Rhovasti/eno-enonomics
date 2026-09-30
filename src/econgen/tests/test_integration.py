from decimal import Decimal
from ..cli import _calculate_supply_from_capacities
from ..models import Capacity, Operator, TechLevel, SimulationConfig
from ..rules import RulesEngine, create_default_rules
from ..taxonomy import create_default_taxonomy
from ..demand import DemandCalculator, create_default_demand_profiles
from ..trade import TradeNetwork
from ..pricing import PriceCalculator


class TestSupplyDemandIntegration:
    """Test integration between supply generation and demand calculation."""

    def test_supply_uses_taxonomy_resource_ids(self):
        """Verify supply generation uses actual taxonomy resource IDs."""
        # Setup
        rules = create_default_rules()
        rules_engine = RulesEngine(rules)

        # Create a test capacity for farming
        capacity = Capacity(
            operator_id="test-op",
            rule_id="farming",
            max_rate=Decimal("10.0"),
            efficiency=Decimal("1.0"),
        )

        # Calculate supply
        supply = _calculate_supply_from_capacities([capacity], [], rules_engine)

        # Verify "food" is in supply, not "farming-output"
        assert "test-op" in supply
        assert "food" in supply["test-op"], (
            f"Expected 'food' in supply, got: {list(supply['test-op'].keys())}"
        )
        assert "farming-output" not in supply["test-op"]
        assert supply["test-op"]["food"] == Decimal("30.0")  # 10 * 1.0 * 3.0 (output ratio)

    def test_supply_demand_resource_alignment(self):
        """Verify supply and demand use matching resource IDs."""
        # Setup components
        taxonomy = create_default_taxonomy()
        rules = create_default_rules()
        rules_engine = RulesEngine(rules)
        demand_profiles = create_default_demand_profiles()
        demand_calc = DemandCalculator(taxonomy, demand_profiles)

        # Create test operator
        operator = Operator(
            operator_id="test-city",
            name="Test City",
            kind="city",
            coord=(0.0, 0.0),
            population=10000,
            tech=TechLevel.MEDIEVAL,
            endowments={},
        )

        # Create capacities for various rules
        capacities = [
            Capacity(
                operator_id="test-city",
                rule_id="farming",
                max_rate=Decimal("5.0"),
                efficiency=Decimal("1.0"),
            ),
            Capacity(
                operator_id="test-city",
                rule_id="toolmaking",
                max_rate=Decimal("3.0"),
                efficiency=Decimal("1.0"),
            ),
        ]

        # Calculate supply and demand
        supply = _calculate_supply_from_capacities(capacities, [operator], rules_engine)
        demand = demand_calc.calculate_all_demand([operator])

        # Verify they have common resources
        supply_resources = set(supply.get("test-city", {}).keys())
        demand_resources = set(demand.get("test-city", {}).keys())
        common_resources = supply_resources & demand_resources

        assert len(common_resources) > 0, (
            f"No common resources! Supply: {supply_resources}, Demand: {demand_resources}"
        )
        assert "food" in common_resources or "tools" in common_resources

    def test_trade_opportunities_generated(self):
        """Verify trade opportunities are generated with fixed supply calculation."""
        # Full integration test
        taxonomy = create_default_taxonomy()
        rules = create_default_rules()
        rules_engine = RulesEngine(rules)
        demand_profiles = create_default_demand_profiles()
        demand_calc = DemandCalculator(taxonomy, demand_profiles)
        config = SimulationConfig()
        price_calc = PriceCalculator(taxonomy, config)

        # Create two operators with different endowments
        operators = [
            Operator(
                operator_id="city-a",
                name="City A",
                kind="city",
                coord=(0.0, 0.0),
                population=20000,
                tech=TechLevel.MEDIEVAL,
                endowments={"agriculture": 10.0},
            ),
            Operator(
                operator_id="city-b",
                name="City B",
                kind="city",
                coord=(1.0, 1.0),
                population=15000,
                tech=TechLevel.MEDIEVAL,
                endowments={"craftsmanship": 8.0},
            ),
        ]

        # Create capacities - much higher production to create surplus
        capacities = [
            Capacity(
                operator_id="city-a",
                rule_id="farming",
                max_rate=Decimal("20000.0"),
                efficiency=Decimal("1.0"),
            ),
            Capacity(
                operator_id="city-b",
                rule_id="toolmaking",
                max_rate=Decimal("10000.0"),
                efficiency=Decimal("1.0"),
            ),
        ]

        # Calculate supply, demand, prices
        supply = _calculate_supply_from_capacities(capacities, operators, rules_engine)
        demand = demand_calc.calculate_all_demand(operators)
        prices = price_calc.calculate_prices(operators, supply, demand)

        # Setup trade network
        trade_network = TradeNetwork(operators, config)

        # Generate trade opportunities (internal method test)
        opportunities = trade_network._generate_trade_opportunities(supply, demand, prices)

        assert len(opportunities) > 0, "No trade opportunities generated after fix!"
        print(f"✅ Generated {len(opportunities)} trade opportunities")


def test_no_weapons_in_tribal_demand():
    """Verify weapons are not in tribal technology demand profiles."""
    demand_profiles = create_default_demand_profiles()

    # Find tribal profile
    tribal_profile = next((p for p in demand_profiles if p.tech == TechLevel.TRIBAL), None)
    assert tribal_profile is not None

    # Verify no weapons in tribal demand
    assert "weapons" not in tribal_profile.per_capita, "Weapons should not appear in tribal demand!"
    print("✅ Weapons correctly excluded from tribal technology")
