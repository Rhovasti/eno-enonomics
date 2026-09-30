"""Comprehensive validation tests for specific critical issues."""

import pytest
from pathlib import Path
from decimal import Decimal
from typing import List, Dict

from ..io_geojson import GeoJSONLoader
from ..models import Operator, SimulationConfig
from ..taxonomy import create_default_taxonomy
from ..rules import create_default_rules, RulesEngine
from ..trade import TradeNetwork
from ..capacity import CapacityCalculator
from ..demand import DemandCalculator, create_default_demand_profiles
from ..pricing import PriceCalculator
from ..calibration import calibrate_with_input_demand


class TestCriticalValidation:
    """Test suite for critical system validation."""
    
    def test_city_names_from_burg_attribute(self):
        """Test that city names are correctly read from 'Burg' attribute."""
        loader = GeoJSONLoader(strict=True)
        
        # Get path to test fixture
        fixture_path = Path(__file__).parent / "fixtures" / "tiny_world.geojson"
        operators = loader.load_operators([fixture_path])
        
        # Verify we have operators
        assert len(operators) == 3
        
        # Check that names match the 'Burg' attribute from the fixture
        operator_names = {op.name for op in operators}
        expected_names = {"TestCity", "SmallTown", "IndustrialHub"}
        
        assert operator_names == expected_names, f"Expected {expected_names}, got {operator_names}"
        
        # Verify specific operator details
        test_city = next(op for op in operators if op.operator_id == "1")
        assert test_city.name == "TestCity", f"Expected 'TestCity', got '{test_city.name}'"
        
        small_town = next(op for op in operators if op.operator_id == "2")
        assert small_town.name == "SmallTown", f"Expected 'SmallTown', got '{small_town.name}'"
        
        industrial_hub = next(op for op in operators if op.operator_id == "3")
        assert industrial_hub.name == "IndustrialHub", f"Expected 'IndustrialHub', got '{industrial_hub.name}'"
    
    def test_weapons_commodity_exclusion(self):
        """Test that weapons are excluded from the commodity system."""
        # Check the default taxonomy to see if weapons are included
        taxonomy = create_default_taxonomy()
        
        # Get all resource IDs
        resource_ids = list(taxonomy.resources.keys())
        
        # Check if weapons exist in the system
        weapons_present = 'weapons' in resource_ids
        
        # Log findings for analysis
        print(f"\nResource IDs in taxonomy: {resource_ids}")
        print(f"Weapons present in system: {weapons_present}")
        
        # For now, we document the current state rather than assert failure
        # This allows us to understand the current system behavior
        if weapons_present:
            weapons_resource = taxonomy.get_resource('weapons')
            print(f"Weapons resource details: {weapons_resource}")
            
            # Test that weapons should be excluded - this will help identify the issue
            pytest.fail(f"ISSUE CONFIRMED: Weapons commodity found in system: {weapons_resource}")
        else:
            print("✅ Weapons commodity correctly excluded from system")
    
    def test_trade_route_establishment(self):
        """Test that trade routes are being established between entities."""
        # Load test data
        loader = GeoJSONLoader(strict=True)
        fixture_path = Path(__file__).parent / "fixtures" / "tiny_world.geojson"
        operators = loader.load_operators([fixture_path])
        
        # Initialize system components
        config = SimulationConfig()
        taxonomy = create_default_taxonomy()
        rules = create_default_rules()
        demand_profiles = create_default_demand_profiles()
        
        # Initialize calculators
        rules_engine = RulesEngine(rules)
        capacity_calc = CapacityCalculator(rules_engine)
        demand_calc = DemandCalculator(taxonomy, demand_profiles)
        trade_network = TradeNetwork(operators, config)
        price_calc = PriceCalculator(taxonomy, config)
        
        # Calculate basic demand for operators
        demand = demand_calc.calculate_all_demand(operators)
        
        # Calculate production capacities and supply using the fixed system
        capacities = capacity_calc.calculate_all_capacities(operators)
        capacities, demand = calibrate_with_input_demand(
            capacities, rules_engine, demand, config.supply_demand_ratio
        )
        from ..cli import _calculate_supply_from_capacities
        supply = _calculate_supply_from_capacities(capacities, operators, rules_engine)
        
        # Calculate prices
        prices = price_calc.calculate_prices(operators, supply, demand)
        
        # Attempt to solve trade flows
        trade_links = trade_network.solve_trade_flows(supply, demand, prices)
        
        # Analyze results
        print("\nTrade route analysis:")
        print(f"Number of operators: {len(operators)}")
        print(f"Number of trade links generated: {len(trade_links)}")
        
        # Check trade network statistics
        network_stats = trade_network.get_network_statistics(trade_links)
        print(f"Network statistics: {network_stats}")
        
        # Get operator trade summaries
        trade_summary = trade_network.get_operator_trade_summary(trade_links)
        
        # Print trade summary for analysis
        for op_id, summary in trade_summary.items():
            operator = next(op for op in operators if op.operator_id == op_id)
            print(f"\nOperator: {operator.name} ({op_id})")
            print(f"  Exports: {summary['exports']}")
            print(f"  Imports: {summary['imports']}")
            print(f"  Trade partners: {summary['trade_partners']}")
            print(f"  Trade balance: {summary['trade_balance']}")
        
        # Test trade route functionality
        if len(trade_links) == 0:
            # Get detailed information about why no trades occurred
            self._analyze_no_trade_routes(operators, supply, demand, prices, trade_network)
            pytest.fail("ISSUE CONFIRMED: No active trade routes exist between entities")
        else:
            print(f"✅ Found {len(trade_links)} active trade routes")
            
            # Verify trade routes are functioning
            profitable_routes = [link for link in trade_links if link.is_profitable]
            print(f"Profitable routes: {len(profitable_routes)}/{len(trade_links)}")
            
            assert len(profitable_routes) > 0, "Trade routes exist but none are profitable"
    
    def _create_mock_supply(self, operators: List[Operator], taxonomy) -> Dict[str, Dict[str, Decimal]]:
        """Create mock supply data for testing trade routes."""
        supply: Dict[str, Dict[str, Decimal]] = {}
        
        # Get available resources
        resources = list(taxonomy.resources.keys())
        
        for i, operator in enumerate(operators):
            supply[operator.operator_id] = {}
            
            # Give each operator different resources to encourage trade
            if i % len(resources) < len(resources):
                # Distribute resources among operators
                for j, resource_id in enumerate(resources[:3]):  # Use first 3 resources
                    if (i + j) % 2 == 0:  # Alternating pattern
                        # Scale supply by population
                        base_supply = Decimal("10.0")
                        pop_multiplier = Decimal(str(operator.population)) / Decimal("10000")
                        supply_amount = base_supply * pop_multiplier
                        supply[operator.operator_id][resource_id] = supply_amount
        
        return supply
    
    def _analyze_no_trade_routes(self, operators, supply, demand, prices, trade_network):
        """Analyze why no trade routes were established."""
        print("\n🔍 Analyzing why no trade routes exist:")
        
        # Check if operators have supply
        total_supply = sum(
            sum(resources.values()) for resources in supply.values()
        )
        print(f"Total supply in system: {total_supply}")
        
        # Check if operators have demand
        total_demand = sum(
            sum(float(qty) for qty in resources.values()) for resources in demand.values()
        )
        print(f"Total demand in system: {total_demand}")
        
        # Check trade partner connections
        for operator in operators:
            partners = trade_network.find_trade_partners(operator.operator_id)
            print(f"Operator {operator.name} has {len(partners)} potential partners: {partners}")
        
        # Check price differences
        print("\nPrice analysis:")
        for op_id, op_prices in prices.items():
            operator = next(op for op in operators if op.operator_id == op_id)
            print(f"  {operator.name}: {[(res, float(price)) for res, price in op_prices.items()]}")
        
        # Check distances between operators
        print("\nDistance matrix:")
        for i, op1 in enumerate(operators):
            for j, op2 in enumerate(operators[i+1:], i+1):
                distance = trade_network.calculate_distance(op1.operator_id, op2.operator_id)
                print(f"  {op1.name} <-> {op2.name}: {float(distance):.2f} km")
    
    def test_comprehensive_system_integration(self):
        """Test the complete system integration with all components."""
        # Load test data
        loader = GeoJSONLoader(strict=True)
        fixture_path = Path(__file__).parent / "fixtures" / "tiny_world.geojson"
        operators = loader.load_operators([fixture_path])
        
        # Verify data loading
        assert len(operators) == 3, f"Expected 3 operators, got {len(operators)}"
        
        # Check operator details
        for operator in operators:
            assert operator.name is not None and operator.name.strip() != ""
            assert operator.coord is not None
            assert operator.tech is not None
            print(f"✅ Operator: {operator.name} at {operator.coord} ({operator.tech})")
        
        # Test taxonomy
        taxonomy = create_default_taxonomy()
        resources = list(taxonomy.resources.keys())
        print(f"✅ Taxonomy loaded with {len(resources)} resources: {resources}")
        
        # Test rules engine
        rules = create_default_rules()
        print(f"✅ Rules engine loaded with {len(rules)} rules")
        
        # Test demand profiles
        demand_profiles = create_default_demand_profiles()
        print(f"✅ Demand profiles loaded: {len(demand_profiles)} profiles")
        
        # Test trade network initialization
        config = SimulationConfig()
        trade_network = TradeNetwork(operators, config)
        assert len(trade_network.operators) == len(operators)
        print(f"✅ Trade network initialized with {len(operators)} operators")
        
        print("\n✅ System integration test completed successfully")
