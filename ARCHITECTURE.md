# Economic Simulation System Architecture

## Overview

The Enonomics system is a deterministic economic simulation engine designed to model trade networks and economic relationships between geographic entities (cities, settlements, etc.) based on GeoJSON input data.

## Core Architecture Principles

### Deterministic Simulation
- All randomness controlled by configurable seed values
- Reproducible results for identical inputs
- Enables A/B testing and validation

### Technology-Stratified Economics
- Three-tier technology progression: Tribal → Medieval → Industrial
- Technology gates determine resource availability and production capabilities
- Population-based technology level inference

### Geographic-Economic Integration
- Real coordinate systems (EPSG:3857 → WGS84 transformation)
- Distance-based trade cost calculations
- Spatial indexing for efficient neighbor queries

## System Components

### 1. Data Loading Layer (`io_geojson.py`)

**Responsibility:** Convert GeoJSON geographic data into economic operators

**Key Functions:**
- Parse FeatureCollection and individual Feature objects
- Transform coordinates from Web Mercator (EPSG:3857) to WGS84 (EPSG:4326)
- Extract and validate operator properties
- Infer economic attributes from geographic features

**Data Transformation Flow:**
```
GeoJSON Feature → Property Extraction → Coordinate Transform → Economic Operator
```

**Critical Implementation Details:**
- Uses `pyproj.Transformer` for accurate coordinate conversion
- Handles both strict and permissive validation modes
- Fallback mechanisms for missing properties
- Robust error handling with detailed logging

**Current Issues:**
- City name extraction correctly uses "Burg" attribute but may have inconsistencies in downstream processing

### 2. Resource Management (`taxonomy.py`)

**Responsibility:** Define and manage the hierarchy of economic resources

**Resource Classification:**
- **Tier 0:** Raw materials (extractable from environment)
- **Tier 1:** Refined goods (require processing)
- **Tier 2:** Advanced goods (require industrial processes)
- **Tier 3:** Luxury goods (high-value, non-essential)

**Technology Constraints:**
- Each resource has minimum technology level requirement
- Technology progression unlocks new resource types
- Prevents anachronistic resource availability

**Resource Attributes:**
```python
Resource(
    resource_id: str,        # Unique identifier
    name: str,              # Human-readable name  
    tier: int,              # Complexity tier (0-3)
    tech_min: TechLevel,    # Minimum technology requirement
    base_price: Decimal,    # Base market value
    transportable: bool,    # Can be traded between locations
    perishable: bool        # Degrades over time
)
```

**Current Issues:**
- Weapons resource marked as Medieval tech but appears in Tribal demand profiles

### 3. Production System (`rules.py`)

**Responsibility:** Model resource transformation through production processes

**Production Rules Structure:**
```python
ProductionRule(
    rule_id: str,                    # Unique identifier
    inputs: Dict[str, Decimal],      # Required input resources
    outputs: Dict[str, Decimal],     # Produced output resources  
    tech_min: TechLevel,            # Minimum technology requirement
    capacity_driver: str,           # Endowment that scales production
    labor_required: Decimal         # Labor cost multiplier
)
```

**Key Features:**
- **DAG Validation:** NetworkX-based cycle detection prevents impossible production chains
- **Technology Gating:** Rules only apply to operators with sufficient tech level
- **Capacity Scaling:** Production limited by operator endowments and population

**Processing Flow:**
```
Operator + Rule → Capacity Calculation → Calibration → Production Rate → Supply Output
```

Raw capacity scales linearly with population (workforce / `labor_required`) and is
multiplied by endowment, tech, infrastructure and specialization factors. It only sets
*relative* productivity. `calibration.py` then scales each rule so that world output of
its primary product equals world demand × `supply_demand_ratio` (default 1.0). Local
differences in productivity become surpluses and deficits for trade to balance.

### 4. Demand Modeling (`demand.py`)

**Responsibility:** Calculate resource consumption requirements for populations

**Demand Calculation:**
```python
per_capita_demand = DemandProfile[tech_level][resource_id]
total_demand = population * per_capita_demand
```

**Technology-Stratified Consumption:**
- Tribal: Focus on basic survival resources (food, tools, shelter materials)
- Medieval: Add processed goods, metal implements, textiles
- Industrial: Include manufactured goods, machinery, luxury items

**Population Scaling:**
- Linear scaling with population size
- Technology level determines consumption basket
- Infrastructure modifiers (ports increase fish demand, etc.)

### 5. Capacity Calculation (`capacity.py`)

**Responsibility:** Determine maximum production rates for operator-rule combinations

**Calculation Framework:**
```python
base_capacity = population * labor_multiplier
endowment_scaling = endowments.get(capacity_driver, default_value)
final_capacity = base_capacity * endowment_scaling * efficiency
```

**Limiting Factors:**
- **Population:** Base labor force size
- **Technology Level:** Access to production rules
- **Endowments:** Resource availability (mining_potential, agriculture, etc.)
- **Infrastructure:** Efficiency modifiers

**Current State:**
- Successfully calculates theoretical production capacities
- Integration with supply calculation may have mapping issues

### 6. Price Calculation (`pricing.py`)

**Responsibility:** Determine local market prices based on supply and demand balance

**Pricing Model:**
```python
supply_ratio = clamp(supply / demand, 0.05, 20)   # no demand + supply -> 20
price_multiplier = (1 / supply_ratio) ** (1 / price_elasticity)
local_price = base_price * price_multiplier * regional_multiplier * operator_modifiers
local_price = clamp(local_price, 0.1 * base_price, 10 * base_price)
```

`price_elasticity` is the price elasticity of demand: higher values give flatter prices.
With the default 1.5 the local multiplier ranges smoothly from 0.14x to 7.4x.

**Economic Factors:**
- **Base Price:** Resource taxonomy defines starting values
- **Supply/Demand Balance:** Scarcity drives price increases
- **Price Elasticity:** Configurable response sensitivity
- **Technology Access:** Higher tech resources command premium prices

**Features:**
- Prevents division by zero with minimum supply thresholds
- Logarithmic scaling for extreme scarcity/abundance
- Per-operator price calculation enables spatial arbitrage

### 7. Trade Network (`trade.py`)

**Responsibility:** Find profitable trade routes between operators

**Spatial Indexing:**
- **KDTree:** Efficient nearest-neighbor queries for trade partner discovery
- **Distance Calculation:** Great circle distance (haversine formula)
- **Trade Radius:** Configurable maximum trade distance
- **Partner Limits:** Maximum number of trading relationships per operator

**Trade Opportunity Detection:**
```python
profit_per_unit = dest_price - source_price - transport_cost
if profit_per_unit > 0:
    # Create trade opportunity
```

**Greedy Optimization:**
1. Generate all possible trade opportunities
2. Sort by profit per unit (descending)
3. Execute trades while supply/demand remain
4. Update remaining quantities after each trade

**Current Critical Issue:**
- **Zero Trade Routes Generated:** Despite seemingly correct logic, no profitable trades are found
- **Potential Causes:** Resource ID mismatches, incorrect supply/demand data, price calculation errors

### 8. Report Generation (`report.py`)

**Responsibility:** Generate human-readable analysis of simulation results

**Report Sections:**
- **Executive Summary:** Key metrics and overview
- **Settlement Analysis:** Population distribution, technology levels
- **Production Analysis:** Capacity utilization, industry specialization
- **Trade Analysis:** Network statistics, flow patterns
- **Economic Indicators:** Price levels, trade volumes

**Output Format:**
- Markdown-formatted reports
- Embedded data tables and statistics
- Integration with Rich console library for colored output

## Data Flow Architecture

### Primary Pipeline
```
GeoJSON → Operators → Capacities → Calibration → Supply
                   → Demand ────────↗          → Prices → Trade Links → Reports
```

### Component Dependencies
```
io_geojson → models
taxonomy → models
rules → models, taxonomy
capacity → models, rules
calibration → models, rules
demand → models, taxonomy  
pricing → models, taxonomy
trade → models, util (distance calculation)
report → All components
```

### Data Structures

#### Core Models (`models.py`)
- **Operator:** Economic entities (cities, settlements)
- **Resource:** Tradeable commodities and goods
- **ProductionRule:** Resource transformation definitions
- **Capacity:** Operator-specific production limits
- **TradeLink:** Individual trade relationships
- **DemandProfile:** Technology-based consumption patterns

#### Configuration (`models.py`)
- **SimulationConfig:** Runtime parameters
- **TechLevel:** Enumerated technology stages with comparison operators

## Performance Characteristics

### Computational Complexity
- **Spatial Queries:** O(log n) via KDTree indexing
- **Trade Opportunity Generation:** O(n²) for all operator pairs
- **Capacity Calculation:** O(n * r) where n = operators, r = rules
- **Price Calculation:** O(n * k) where k = resources

### Memory Usage
- **Operator Storage:** O(n) with detailed geographic and economic data
- **Trade Network:** O(n²) worst case, typically much smaller due to distance limits
- **Caching:** Trade partner relationships cached to reduce computation

### Scalability Limits
- **Current Testing:** 140+ operators handled successfully
- **Memory Bottlenecks:** Trade opportunity matrix for large networks
- **Processing Time:** Linear scaling with operator count for most operations

## Known Architectural Issues

### 1. Resource ID Mapping Inconsistencies
Different components may use different resource identification schemes:
- **Taxonomy:** Uses clean resource_id strings
- **Supply Calculation:** May create derived IDs like "{rule_id}-output"
- **Demand Profiles:** References taxonomy resource_id values

### 2. Supply/Demand Data Structure Misalignment
Components expect consistent nested dictionary structures:
```python
# Expected format
supply: Dict[operator_id, Dict[resource_id, quantity]]
demand: Dict[operator_id, Dict[resource_id, quantity]]
```

### 3. Trade Flow Solver Logic Gap
The trade network solver may have logical errors in:
- Resource matching between supply and demand
- Profitability calculation
- Quantity allocation and updating

## Technology Debt and Improvements

### Immediate Priorities
1. **Fix Trade Route Generation:** Root cause analysis and resolution
2. **Resource ID Standardization:** Consistent naming across all components  
3. **Integration Testing:** End-to-end validation of data flow

### Medium-term Improvements
- **Multi-step Production:** Chain multiple production rules
- **Dynamic Pricing:** Time-based price evolution
- **Transportation Networks:** Explicit road/sea route modeling
- **Economic Events:** Disruptions, discoveries, technological advancement

### Long-term Vision
- **AI-driven Economy:** Machine learning for demand prediction
- **Political Systems:** Taxation, trade policies, conflicts
- **Dynamic Geography:** Seasonal changes, resource depletion
- **Multi-scale Modeling:** Individual agents within settlement economies

## Testing Strategy

### Unit Testing
- Individual component functionality
- Model validation and edge cases
- Mathematical calculations (pricing, distance, etc.)

### Integration Testing  
- Component interaction validation
- Data flow integrity
- End-to-end pipeline execution

### Performance Testing
- Large dataset handling (1000+ operators)
- Memory usage profiling
- Execution time benchmarking

### Validation Testing
- Economic reality checks
- Historical scenario matching
- Expert domain knowledge validation

## Configuration and Extensibility

### YAML Configuration
```yaml
simulation:
  max_trade_neighbors: 8
  max_trade_radius_km: 800
  min_trade_quantity: 0.5
  transport_cost_per_km: 0.02

resources:
  - resource_id: "custom-resource"
    name: "Custom Resource"
    # ... additional properties

rules:
  - rule_id: "custom-production"
    inputs: {"input-resource": 1.0}
    outputs: {"output-resource": 1.5}
    # ... additional properties
```

### Extension Points
- **Custom Resources:** Add new resource types via configuration
- **Production Rules:** Define new transformation processes
- **Demand Profiles:** Technology-specific consumption patterns
- **Endowment Inference:** Geographic feature-based resource availability

This architecture provides a solid foundation for economic simulation while identifying critical areas requiring immediate attention to achieve full functionality.