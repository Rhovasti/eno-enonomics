# PRP-REVISION-001: Fix Trade Route Generation System

## Problem Statement
The Enonomics economic simulation currently generates **0 trade routes** despite having functional supply/demand calculation components. The root cause is a **resource ID mapping inconsistency** between the supply generation and demand calculation systems.

### Critical Issue
```python
# CURRENT BROKEN STATE (cli.py:313-331)
supply = {"TestCity": {"farming-output": 10.0, "toolmaking-output": 5.0}}  # ❌ Synthetic IDs
demand = {"SmallTown": {"food": 8.0, "tools": 3.0}}                        # ✅ Taxonomy IDs

# Result: No common resources = 0 trade opportunities
```

## Root Cause Analysis

The `_calculate_supply_from_capacities()` function in `/root/Eno/Enonomics/src/econgen/cli.py:313-331` incorrectly generates resource IDs:

```python
# BROKEN CODE (line 326)
resource_id = f"{rule_id}-output"  # Creates "farming-output" instead of "food"
```

This should instead iterate through the actual production rule outputs which contain proper taxonomy resource IDs.

## Solution Implementation Blueprint

### 1. Fix Supply Calculation (PRIMARY FIX)

**Location**: `/root/Eno/Enonomics/src/econgen/cli.py:313-331`

**Current Broken Implementation**:
```python
def _calculate_supply_from_capacities(capacities: List, operators: List) -> dict:
    """Calculate supply quantities from production capacities."""
    supply = {}
    
    for capacity in capacities:
        if capacity.operator_id not in supply:
            supply[capacity.operator_id] = {}
        
        # Simple supply calculation: use max_rate as production
        # In a full simulation, this would consider input availability
        production = capacity.max_rate * capacity.efficiency
        
        # For now, assume single-output rules (could be extended)
        rule_id = capacity.rule_id
        resource_id = f"{rule_id}-output"  # ❌ BROKEN: Simplified mapping
        
        supply[capacity.operator_id][resource_id] = production
    
    return supply
```

**Fixed Implementation Pseudocode**:
```python
def _calculate_supply_from_capacities(capacities: List, operators: List, rules_engine: RulesEngine) -> dict:
    """Calculate supply quantities from production capacities."""
    supply = {}
    
    for capacity in capacities:
        if capacity.operator_id not in supply:
            supply[capacity.operator_id] = {}
        
        # Get the actual rule to access its outputs
        rule = rules_engine.get_rule(capacity.rule_id)
        if not rule:
            continue
            
        # Calculate base production
        production = capacity.max_rate * capacity.efficiency
        
        # Iterate through actual rule outputs (proper resource IDs)
        for resource_id, output_ratio in rule.outputs.items():
            # Scale production by output ratio
            resource_production = production * output_ratio
            
            if resource_id in supply[capacity.operator_id]:
                supply[capacity.operator_id][resource_id] += resource_production
            else:
                supply[capacity.operator_id][resource_id] = resource_production
    
    return supply
```

**Key Changes**:
1. Add `rules_engine` parameter to access production rules
2. Look up actual rule using `capacity.rule_id`
3. Iterate through `rule.outputs` dictionary which contains proper taxonomy resource IDs
4. Support multi-output rules by iterating all outputs
5. Accumulate production for resources that appear in multiple rules

### 2. Update Function Call Sites

**Location**: `/root/Eno/Enonomics/src/econgen/cli.py` (run function)

Find where `_calculate_supply_from_capacities` is called and add `rules_engine` parameter:
```python
# Around line 150-160
supply = _calculate_supply_from_capacities(capacities, operators, rules_engine)
```

### 3. Remove Weapons from Tribal Technology

**Files to Modify**:

1. **`/root/Eno/Enonomics/src/econgen/taxonomy.py:219-226`** - Remove weapons Resource creation
2. **`/root/Eno/Enonomics/src/econgen/rules.py:283-293`** - Remove weaponsmithing ProductionRule
3. **`/root/Eno/Enonomics/src/econgen/demand.py:374-379`** - Remove weapons from TRIBAL DemandProfile

### 4. Add Integration Tests

**Create**: `/root/Eno/Enonomics/src/econgen/tests/test_integration.py`

```python
import pytest
from decimal import Decimal
from pathlib import Path
from src.econgen.cli import _calculate_supply_from_capacities
from src.econgen.models import Capacity, Operator, TechLevel
from src.econgen.rules import RulesEngine, create_default_rules
from src.econgen.taxonomy import create_default_taxonomy
from src.econgen.demand import DemandCalculator, create_default_demand_profiles
from src.econgen.trade import TradeNetwork
from src.econgen.models import SimulationConfig
from src.econgen.price import PriceCalculator


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
            efficiency=Decimal("1.0")
        )
        
        # Calculate supply
        supply = _calculate_supply_from_capacities([capacity], [], rules_engine)
        
        # Verify "food" is in supply, not "farming-output"
        assert "test-op" in supply
        assert "food" in supply["test-op"], f"Expected 'food' in supply, got: {list(supply['test-op'].keys())}"
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
            lat=0.0,
            lon=0.0,
            population=10000,
            tech=TechLevel.MEDIEVAL,
            endowments={}
        )
        
        # Create capacities for various rules
        capacities = [
            Capacity(operator_id="test-city", rule_id="farming", max_rate=Decimal("5.0"), efficiency=Decimal("1.0")),
            Capacity(operator_id="test-city", rule_id="toolmaking", max_rate=Decimal("3.0"), efficiency=Decimal("1.0")),
        ]
        
        # Calculate supply and demand
        supply = _calculate_supply_from_capacities(capacities, [operator], rules_engine)
        demand = demand_calc.calculate_all_demand([operator])
        
        # Verify they have common resources
        supply_resources = set(supply.get("test-city", {}).keys())
        demand_resources = set(demand.get("test-city", {}).keys())
        common_resources = supply_resources & demand_resources
        
        assert len(common_resources) > 0, f"No common resources! Supply: {supply_resources}, Demand: {demand_resources}"
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
                lat=0.0,
                lon=0.0,
                population=20000,
                tech=TechLevel.MEDIEVAL,
                endowments={"agriculture": 10.0}
            ),
            Operator(
                operator_id="city-b",
                name="City B",
                lat=1.0,
                lon=1.0,
                population=15000,
                tech=TechLevel.MEDIEVAL,
                endowments={"craftsmanship": 8.0}
            )
        ]
        
        # Create capacities
        capacities = [
            Capacity(operator_id="city-a", rule_id="farming", max_rate=Decimal("10.0"), efficiency=Decimal("1.0")),
            Capacity(operator_id="city-b", rule_id="toolmaking", max_rate=Decimal("5.0"), efficiency=Decimal("1.0")),
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
```

## Existing Context & Patterns

### Model Structure (from `/root/Eno/Enonomics/src/econgen/models.py`)
```python
class ProductionRule(BaseModel):
    """Production transformation rules."""
    rule_id: str = Field(..., pattern=r"^[a-z0-9-]+$")
    name: str
    inputs: Dict[str, Decimal]  # resource_id -> quantity
    outputs: Dict[str, Decimal]  # resource_id -> quantity  ← CRITICAL: outputs use taxonomy IDs
    tech_min: TechLevel
    # ... other fields
```

### RulesEngine Pattern (from `/root/Eno/Enonomics/src/econgen/rules.py`)
```python
class RulesEngine:
    def __init__(self, rules: List[ProductionRule]):
        self.rules = {rule.rule_id: rule for rule in rules}
    
    def get_rule(self, rule_id: str) -> Optional[ProductionRule]:
        """Get a rule by ID."""
        return self.rules.get(rule_id)
```

### Working Components (DO NOT BREAK)
- ✅ GeoJSON loading with coordinate transformation
- ✅ Resource taxonomy system and validation  
- ✅ Production rules engine with DAG validation
- ✅ Economic operator modeling and population inference
- ✅ Spatial trade network and distance calculations
- ✅ Price calculation and market dynamics
- ✅ Report generation and data export

## Implementation Tasks

1. **Fix supply calculation** in `cli.py:_calculate_supply_from_capacities()`
   - Add rules_engine parameter
   - Look up actual production rules
   - Use rule.outputs dictionary for resource IDs
   
2. **Update function calls** to pass rules_engine parameter
   - Modify the run() function call site
   
3. **Remove weapons from tribal tier**
   - Remove from taxonomy.py default resources
   - Remove weaponsmithing from rules.py
   - Remove from tribal demand profile in demand.py
   
4. **Add integration tests** in `test_integration.py`
   - Test supply uses correct resource IDs
   - Test supply/demand alignment
   - Test trade opportunity generation
   - Test weapons exclusion from tribal

5. **Run validation suite**
   - Execute existing test_validation.py
   - Verify trade routes > 0 on tiny_world.geojson

## Validation Gates

```bash
# 1. Syntax and style check
uv run ruff check --fix src/

# 2. Run unit tests
uv run pytest src/econgen/tests/test_models.py -v

# 3. Run integration tests (new)
uv run pytest src/econgen/tests/test_integration.py -v

# 4. Run validation tests
uv run pytest src/econgen/tests/test_validation.py::TestCriticalValidation::test_trade_route_establishment -v

# 5. End-to-end test
uv run python -m src.econgen.cli run --input data/tiny_world.geojson --output out/test_fix

# Expected output:
# Trade Links: 3-5  ✅ (was 0)
# Generated 12+ potential trade opportunities ✅ (was 0)
```

## Error Handling Considerations

1. **Null checks**: Ensure rule lookup handles missing rules gracefully
2. **Division by zero**: Check for zero efficiency/max_rate
3. **Missing outputs**: Handle rules with empty outputs dictionary
4. **Type safety**: Maintain Decimal precision throughout calculations

## Performance Notes

- Current system handles 3-140 operators efficiently
- Trade opportunity calculation is O(n²) - acceptable for current scale
- Resource ID lookup is O(1) using dictionary access
- No performance regression expected from fix

## External References

### Best Practices for Economic Simulations
- **Resource Consistency**: https://towardsdatascience.com/supply-chain-optimization-with-python-23ae9b28fd0b
- **Agent-Based Modeling**: https://github.com/thonmakerformvp/econ-sim
- **Supply/Demand Matching**: https://intro.quantecon.org/intro_supply_demand.html

### Python Economic Simulation Patterns
1. Use consistent identifiers across all system components
2. Implement feedback loops between supply and demand
3. Validate data flow at integration points
4. Use type hints and Pydantic models for validation

## Success Criteria

✅ Trade route generation produces > 0 results on test data
✅ Supply/demand resource IDs align correctly 
✅ All integration tests pass
✅ No weapons in tribal technology demand
✅ System maintains current performance
✅ All existing functionality remains intact

## Common AI Assistant Pitfalls to Avoid

❌ Don't create new files unnecessarily - edit existing components
❌ Don't assume test frameworks - use existing pytest setup
❌ Don't break working components while fixing trade solver
❌ Don't add features - focus only on critical fixes
❌ Don't update pyproject.toml directly - use `uv add` for packages
❌ Don't ignore line length limits (100 chars max)

## Confidence Score: 9/10

This PRP provides comprehensive context for successful one-pass implementation. The only uncertainty is potential edge cases in the production rule outputs handling, but the integration tests will catch these.