# Enonomics - Economic Worldbuilding Generator

A deterministic economic simulation system that analyzes GeoJSON city data to generate realistic trade networks, production systems, and market dynamics for worldbuilding and game development.

## Current System Status

**Version:** 0.1.0  
**Status:** Active Development - Core systems implemented with known issues

### Quick Start

```bash
# Install dependencies
uv sync

# Run simulation with sample data
uv run python -m src.econgen.cli run --input data/performance_test.geojson --output out/results

# Validate GeoJSON files
uv run python -m src.econgen.cli validate --input Data/kaupungit.geojson

# Generate configuration template
uv run python -m src.econgen.cli config-template --output my_config.yaml
```

## System Architecture Overview

The simulation operates through a multi-stage pipeline that processes GeoJSON city data to generate economic relationships:

```
GeoJSON Input → Operators → Production → Demand → Calibration → Pricing → Trade Network → Reports
```

### Core Components

1. **Data Loading** (`io_geojson.py`) - Converts GeoJSON features to economic operators
2. **Resource System** (`taxonomy.py`) - Manages resource definitions and relationships
3. **Production Rules** (`rules.py`) - Defines transformation processes between resources
4. **Capacity Calculation** (`capacity.py`) - Determines production capabilities
5. **Demand Modeling** (`demand.py`) - Calculates per-capita resource consumption
6. **Price Calculation** (`pricing.py`) - Determines market prices based on supply/demand
7. **Trade Network** (`trade.py`) - Finds profitable trade routes using spatial indexing
8. **Report Generation** (`report.py`) - Creates comprehensive analysis reports

## Data Models

### Technology Levels
```python
TechLevel.TRIBAL     # Basic tools, organic agriculture
TechLevel.MEDIEVAL   # Metal working, complex crafts  
TechLevel.INDUSTRIAL # Machinery, mass production
```

### Resource Taxonomy
- **Tier 0:** Raw materials (wood, stone, iron-ore, food, fish)
- **Tier 1:** Refined goods (tools, weapons, textiles)
- **Tier 2:** Advanced goods (steel, machinery) 
- **Tier 3:** Luxury goods (jewelry)

### Economic Operators
Cities and settlements with:
- Geographic coordinates (converted from EPSG:3857 to WGS84)
- Technology level (inferred from population)
- Resource endowments (derived from geographic features)
- Infrastructure flags (port, capital, walls, etc.)

## Known Issues

### 1. Weapons in Demand Profiles (Minor)
**Status:** OPEN - design decision pending

`weapons` was removed from the default taxonomy and from `config/econ.yaml` (see
`PRPs/REVISION-001.md`), and the tribal profile no longer demands it. The medieval and industrial profiles and several
demand modifiers in `demand.py` still reference `weapons` (and `armor`), which logs an
"unknown resources" warning at runtime.

### Resolved
- **YAML config vs. built-in defaults:** `config/econ.yaml` now matches the defaults exactly
  (enforced by `test_config.py`). The YAML-only extraction rules (forestry, quarrying,
  iron-mining, coal-mining) moved into the defaults; `weapons`/`weaponsmithing` left the YAML.
- **Run-to-run output order:** set iteration in pricing and trade is sorted, so data outputs
  are byte-identical for the same input (only the report timestamp changes).
- **City names:** read from the `Burg` attribute (covered by `test_city_names_from_burg_attribute`).
- **Missing default resources:** `seed`, `fiber`, `coal`, `precious-metals`, `gems` and
  `slag` are now in the default taxonomy, so every default rule references known resources.
- **Tech gating:** rule and resource eligibility now follow tech order (`test_rules.py`).
- **Zero trade after the tech-gating fix:** production is now calibrated to demand
  (`calibration.py`) and trade uses net surplus/deficit. `Data/kaupungit.geojson` yields
  95 links (food, fish, tools, textiles, jewelry); `data/performance_test.geojson` 231.
- **Prices pinned at the cap:** the scarcity curve applied its multiplier twice, had step
  jumps and could go negative. It is now a smooth constant-elasticity curve (see
  `ARCHITECTURE.md`); no trade link on the bundled datasets imports at the cap.

## Successfully Implemented Features

### ✅ GeoJSON Data Loading
- Robust parsing of FeatureCollection and individual Features
- Coordinate transformation from Web Mercator to WGS84
- Property extraction with intelligent defaults
- Comprehensive error handling and validation modes

### ✅ Resource System
- Hierarchical resource taxonomy (4 tiers)
- Technology-gated availability
- Transportability and perishability flags
- Base price definitions

### ✅ Production Rules Engine
- DAG validation prevents circular dependencies
- Technology-level constraints
- Input/output resource mapping
- Capacity drivers and labor requirements

### ✅ Spatial Trade Network
- KDTree-based nearest neighbor search
- Configurable trade radius and partner limits
- Great circle distance calculations
- Partner caching for performance

### ✅ Economic Operator Modeling
- Population-based technology inference
- Geographic endowment derivation
- Infrastructure feature detection
- Comprehensive attribute preservation

### ✅ Configuration System
- YAML-based configuration files
- Default taxonomies and rule sets
- Environment-specific parameters
- Template generation

### ✅ Report Generation
- Markdown-formatted analysis reports
- Trade network statistics
- Settlement rankings and distributions
- Production capacity analysis

## System Workflow (Design Intent)

1. **Data Ingestion:** Load GeoJSON files containing city/settlement data
2. **Operator Creation:** Convert geographic features to economic operators
3. **Capacity Calculation:** Determine production capabilities based on population, tech level, and endowments
4. **Demand Calculation:** Calculate resource needs based on population and technology
5. **Supply Determination:** Calculate surplus production available for trade
6. **Price Calculation:** Determine local prices based on supply/demand balance
7. **Trade Network Solving:** Find profitable trade routes between operators
8. **Report Generation:** Create comprehensive economic analysis

## Data Structure Details

### Operator Model
```python
Operator(
    operator_id: str,           # Unique identifier
    name: str,                  # Display name (from "Burg" field)
    kind: Literal["city", ...], # Operator type
    tech: TechLevel,            # Technology level
    coord: Tuple[float, float], # (lat, lon) in WGS84
    population: int,            # Population count
    endowments: Dict[str, Decimal], # Resource availability
    # Infrastructure flags
    capital: bool, port: bool, walls: bool, ...
)
```

### Trade Link Model
```python
TradeLink(
    source_id: str,          # Exporting operator
    dest_id: str,            # Importing operator  
    resource_id: str,        # Traded resource
    quantity: Decimal,       # Trade volume
    distance_km: Decimal,    # Transport distance
    transport_cost: Decimal, # Cost per unit distance
    price_source: Decimal,   # Export price
    price_dest: Decimal,     # Import price
    profit_margin: Decimal   # Total profit
)
```

## Development Status

### Phase 1: Core Infrastructure ✅ COMPLETE
- [x] Data models and validation
- [x] GeoJSON loading and parsing
- [x] Resource taxonomy system
- [x] Production rules engine
- [x] Configuration management

### Phase 2: Economic Calculation ⚠️ PARTIAL
- [x] Capacity calculation
- [x] Demand modeling  
- [x] Price calculation
- [x] Supply/demand calibration (`supply_demand_ratio`, default 1.0)
- [x] Trade flow solving on net surplus/deficit
- [x] Constant-elasticity price curve

### Phase 3: Analysis and Output ✅ COMPLETE
- [x] Trade network statistics
- [x] Report generation
- [x] Data export (JSON/JSONL)

## Contributing

See `CLAUDE.md` for comprehensive development guidelines including:
- Code structure and modularity requirements
- Testing strategies (TDD approach)
- Style conventions and naming
- Performance considerations

### Quick Development Setup
```bash
# Clone and setup
git clone <repository>
cd Enonomics
uv sync

# Run tests
uv run pytest

# Format code  
uv run ruff format .

# Check linting
uv run ruff check .
```

## License

[License information to be added]