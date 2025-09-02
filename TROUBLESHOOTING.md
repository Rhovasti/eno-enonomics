# Troubleshooting Guide

This document provides detailed analysis and debugging approaches for known issues in the Economic Simulation System.

## Critical Issue #1: No Active Trade Routes Generated

**Symptom:** Trade network solver consistently produces 0 trade links  
**Impact:** Core functionality broken - economic simulation incomplete  
**Status:** Under investigation

### Evidence
- Performance test (140 operators): 0 trade routes
- Small test (3 operators): 0 trade routes
- All operators have calculated capacities and demand profiles
- Price calculations complete successfully

### Debugging Approach

#### Step 1: Verify Supply/Demand Data Integrity

**Check supply calculation in CLI (`cli.py:313-331`):**
```python
def _calculate_supply_from_capacities(capacities: List, operators: List) -> dict:
    supply = {}
    for capacity in capacities:
        # Simplified mapping: rule_id -> resource_id
        resource_id = f"{rule_id}-output"  # ⚠️ SUSPICIOUS
        supply[capacity.operator_id][resource_id] = production
```

**Potential Issue:** Resource ID mapping inconsistency
- Supply uses `"{rule_id}-output"` format
- Demand uses taxonomy resource IDs directly
- Trade solver requires matching resource IDs

#### Step 2: Trace Trade Opportunity Generation

**Check `trade.py:172-221` - `_generate_trade_opportunities`:**
```python
# Find common resources (source has surplus, dest has demand)
source_resources = set(supply[source_id].keys())
dest_resources = set(demand[dest_id].keys()) 
common_resources = source_resources & dest_resources  # ⚠️ May be empty
```

**Diagnostic Commands:**
```bash
# Add debug logging to trade.py
import logging
logger.debug(f"Source resources: {source_resources}")
logger.debug(f"Dest resources: {dest_resources}")
logger.debug(f"Common resources: {common_resources}")
```

#### Step 3: Validate Price Calculations

**Check price data structure matches expectation:**
```python
# Expected: prices[operator_id][resource_id] = price_value
# Verify in trade.py:207-208
source_price = prices.get(source_id, {}).get(resource_id, Decimal("1"))
dest_price = prices.get(dest_id, {}).get(resource_id, Decimal("1"))
```

### Likely Root Cause Analysis

#### Theory 1: Resource ID Mismatch (HIGH PROBABILITY)
```python
# Supply calculation creates synthetic IDs
supply = {"city1": {"toolmaking-output": 10.0}}

# Demand uses taxonomy resource IDs  
demand = {"city2": {"tools": 5.0}}

# No intersection: {"toolmaking-output"} ∩ {"tools"} = ∅
```

**Fix Approach:** Modify supply calculation to use output resource IDs from production rules
```python
# In _calculate_supply_from_capacities
rule = rules_engine.get_rule(capacity.rule_id)
for output_resource_id, output_quantity in rule.outputs.items():
    production = capacity.max_rate * capacity.efficiency * output_quantity
    supply[capacity.operator_id][output_resource_id] = production
```

#### Theory 2: Empty Supply/Demand Data (MEDIUM PROBABILITY)
- Capacity calculation succeeds but produces zero quantities
- Demand calculation fails to generate realistic consumption
- Price calculation creates unrealistic values

**Diagnostic:**
```python
# Add to CLI after supply/demand calculation
logger.info(f"Total supply entries: {sum(len(resources) for resources in supply.values())}")
logger.info(f"Total demand entries: {sum(len(resources) for resources in demand.values())}")
logger.info(f"Sample supply: {dict(list(supply.items())[:3])}")
logger.info(f"Sample demand: {dict(list(demand.items())[:3])}")
```

#### Theory 3: Transport Cost Exceeds Profit (LOW PROBABILITY)
- Distance calculations correct but transport costs too high
- Price differences insufficient to overcome shipping costs

**Check:** Transport cost configuration in `SimulationConfig`:
- `transport_cost_per_km: 0.02` (reasonable)
- `max_trade_radius_km: 800` (reasonable for medieval/fantasy setting)

### Systematic Debugging Steps

1. **Add comprehensive logging to trade network solver**
2. **Verify resource ID consistency across all components**  
3. **Check for empty or malformed supply/demand data**
4. **Validate price calculation produces reasonable values**
5. **Test with simplified single-resource scenario**

---

## Issue #2: City Names from Wrong Attribute

**Symptom:** City name extraction may have inconsistencies  
**Impact:** Data integrity and user experience  
**Status:** Partially resolved

### Analysis

**Current Implementation (`io_geojson.py:130`):**
```python
name = props.get("Burg", props.get("name", f"Unknown_{operator_id}"))
```

**GeoJSON Data Structure:**
```geojson
{
  "properties": {
    "fid": 1,
    "Id": 1,
    "Burg": "Jouy",        # ✅ Correct source
    "name": null,          # ❌ Often null/empty
    "Population": 13872
  }
}
```

### Verification

**Check all operators have correct names:**
```python
# In validation or report generation
for op in operators:
    if op.name.startswith("Unknown_"):
        logger.warning(f"Operator {op.operator_id} using fallback name")
    if "Burg" in original_properties and op.name != original_properties["Burg"]:
        logger.error(f"Name mismatch: expected {original_properties['Burg']}, got {op.name}")
```

### Status
- **Primary extraction logic is correct**
- **Need verification that downstream processing preserves names**
- **Low priority - system functions correctly with current implementation**

---

## Issue #3: Weapons in Tribal Technology

**Symptom:** Medieval weapons appear in Tribal demand profiles  
**Impact:** Logical inconsistency in world simulation  
**Status:** Design decision needed

### Analysis

**Resource Definition (`taxonomy.py:220-227`):**
```python
Resource(
    resource_id="weapons",
    name="Weapons", 
    tier=1,                     # Refined good
    tech_min=TechLevel.MEDIEVAL, # Requires medieval tech
    base_price=Decimal("8.0"),
    transportable=True,
    perishable=False
)
```

**Demand Profile Logic (`demand.py`):**
```python
# Should filter resources by technology level
available_resources = [r for r in resources if r.tech_min <= operator.tech]
```

### Root Cause Investigation

#### Check Demand Profile Generation

**Verify technology filtering in `create_default_demand_profiles()`:**
```python
def create_default_demand_profiles() -> List[DemandProfile]:
    profiles = [
        DemandProfile(
            tech=TechLevel.TRIBAL,
            per_capita={
                "wood": Decimal("0.5"),
                "tools": Decimal("0.1"), 
                "food": Decimal("2.0")
                # ❌ Should NOT include "weapons": Decimal("0.05")
            }
        )
    ]
```

#### Check Runtime Demand Calculation

**Verify `DemandCalculator.calculate_demand()` respects tech levels:**
```python
def calculate_demand(self, operator: Operator) -> Dict[str, Decimal]:
    available_resources = self.taxonomy.get_resources_by_tech(operator.tech)
    # Only calculate demand for tech-appropriate resources
```

### Fix Approach

1. **Audit all default demand profiles** - Remove tech-inappropriate resources
2. **Add validation** - Demand calculator should assert all requested resources are available
3. **Consider tribal weapons** - Maybe add "primitive_weapons" resource for tribal tech

### Design Questions

- **Should tribal societies have primitive weapons?** (spears, clubs, bows)
- **Should there be technology progression for similar resource types?**
- **How to handle cultural/regional differences in technology adoption?**

---

## General Debugging Strategies

### Logging Configuration

**Add detailed logging to key components:**
```python
# In each major component
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Key log points:
logger.debug(f"Processing {len(items)} items")
logger.info(f"Generated {len(results)} results") 
logger.warning(f"Unexpected condition: {condition}")
logger.error(f"Failed to process {item}: {error}")
```

### Data Validation Checkpoints

**Add validation after each major processing step:**
```python
def validate_supply_demand_structure(supply, demand):
    """Ensure consistent data structure across components."""
    for operator_id in supply:
        assert isinstance(supply[operator_id], dict)
        for resource_id, quantity in supply[operator_id].items():
            assert isinstance(resource_id, str)
            assert isinstance(quantity, Decimal)
            assert quantity >= 0
```

### Unit Test Coverage

**Focus testing on component boundaries:**
```python
def test_supply_demand_resource_id_consistency():
    """Ensure supply and demand use same resource identifiers."""
    supply = calculate_supply(test_capacities, test_operators)
    demand = calculate_demand(test_operators) 
    
    all_supply_resources = set()
    for resources in supply.values():
        all_supply_resources.update(resources.keys())
        
    all_demand_resources = set() 
    for resources in demand.values():
        all_demand_resources.update(resources.keys())
        
    intersection = all_supply_resources & all_demand_resources
    assert len(intersection) > 0, "No common resources between supply and demand"
```

### Performance Profiling

**Add timing measurements to identify bottlenecks:**
```python
import time
from contextlib import contextmanager

@contextmanager
def timer(description):
    start = time.time()
    yield
    elapsed = time.time() - start
    logger.info(f"{description}: {elapsed:.2f}s")

# Usage
with timer("Trade network solving"):
    trade_links = trade_network.solve_trade_flows(supply, demand, prices)
```

---

## Resolution Priority

### High Priority (Core Functionality)
1. **Trade route generation failure** - System unusable without working trade solver
2. **Resource ID consistency** - Fundamental data integrity issue

### Medium Priority (Data Quality)  
3. **City name extraction verification** - Affects user experience
4. **Supply/demand calculation accuracy** - Economic realism

### Low Priority (Logical Consistency)
5. **Technology-resource alignment** - World-building quality
6. **Performance optimization** - Scalability concerns

### Monitoring and Metrics

**Add system health checks:**
```python
def generate_system_health_report(operators, trade_links, capacities):
    """Generate diagnostic metrics for system health."""
    return {
        "operators_loaded": len(operators),
        "trade_routes_active": len(trade_links), 
        "trade_routes_per_operator": len(trade_links) / len(operators) if operators else 0,
        "capacities_calculated": len(capacities),
        "avg_capacity_utilization": calculate_avg_utilization(capacities),
        "resource_coverage": calculate_resource_coverage(operators),
    }
```

This troubleshooting guide provides systematic approaches to diagnosing and resolving the known issues, with emphasis on the critical trade route generation problem.