# Development Status Report

**Project:** Enonomics - Economic Worldbuilding Generator  
**Date:** 2026-09-30 (previous report: 2025-08-10)  
**Version:** 0.1.0

## Current State Summary

The pipeline runs end-to-end on all bundled datasets and produces tech-consistent trade.
The trade links reported in `TRADE_NETWORK_FIX.md` came from a tech-gating bug. Fixing it
dropped trade to 0, and production has since been recalibrated against demand (see Issue #1).

## Alchemical economy (2026-09-30, full-stack layer)

The Periodical System of Eno (`fantastical.py`, lore in `w Periodical system of Eno.md`)
is now part of the default economy and runs through every layer:

- **Catalog**: 8 alchemical components + 8 periodic elements + 4 alchemical stuffs as
  resources/rules/demand, merged into `config/econ.yaml` in lockstep (config parity test).
- **Endowments**: inferred from geography in both input routes — GeoJSON features and the
  143 citystate `.md` profiles (Rime on the dark side vs Ash on the sun side by longitude,
  Sap with vegetation, Pitch at coasts, Phos at industrial sites, deterministic element
  deposits for mining cities, rare Mucus/Mold).
- **Dynamics** (`dynamics/`, `citystates/simulator.py`): crafted production consumes its
  inputs — the adapter derives per-unit input rates from the production rules, and both
  Minsky builders gate production on input availability `S/(S+0.1·ref)` while draining the
  input stocks. Generated Minsky parameter names must stay alphanumeric (underscore reads
  as a subscript separator, so `variableValues` misses the `init` and the value stays 0).
- **Markets** (`citystates/market.py`): world prices carry an input-cost floor
  `(1+margin)·Σ input_price·qty`, so component scarcity propagates into stuffs (and mundane
  chains like wood → tools → steel → machinery).
- **Finance** (`financial/`): alchemical value added is a sector of its own — GDP carve-out
  by tier (components/elements/stuffs), guild wages/consumption/dividends, and an
  Alchemists' Guild column in the Godley transactions matrix that balances exactly.
- **CLI**: `simulate` plus `citystate-sim|dynamic|chronicle|financial|governance` (CLI
  split into `cli_common`/`cli`/`cli_dynamics`/`cli_citystates`; `governance_types` holds
  the catalog tables).

On geography-only datasets (no worldbuilder stocks), sap and element deposits fall back to
vegetation and mining potential, and an element coverage pass ensures each core element has
at least one medieval+ mining city. On `kaupungit` alchemical trade stays thin: its mountain
cities are mostly tribal, so each element comes from only 1-3 distant cities.

Minsky-dependent tests skip without a local pyminsky build; citystate-corpus tests skip
without the Worldbuilder2 profiles folder. CI runs ruff check, ruff format, mypy and pytest.

### Health check (2026-09-30)

| Check | Result |
|---|---|
| `uv run pytest` | 123 passed, 19 skipped (Minsky / citystate corpus) |
| CLI `run` on `data/performance_test.geojson` | 793 trade links, 318 of them alchemical |
| CLI `run` on `Data/kaupungit.geojson` | 72 links; every alchemical good produced, 6 alchemical links (few, distant producers) |
| Default run vs. `--config config/econ.yaml` | Identical data outputs |
| `uv run ruff check .` | Passing |
| `uv run ruff format --check .` | Passing (line length 100, set in `pyproject.toml`) |
| `uv run mypy src/` | Passing (type stubs for networkx and scipy added as dev deps) |
| CI | GitHub Actions (`.github/workflows/ci.yml`): ruff check, ruff format, mypy, pytest |

### Changes in this update
- `pytest.ini` header corrected (`[tool:pytest]` -> `[pytest]`) so its settings apply.
- Tech-level comparisons fixed: models store tech as plain strings, which compared
  alphabetically. Rule/resource eligibility now follows tribal < medieval < industrial.
- Default taxonomy gained `seed`, `fiber`, `coal`, `precious-metals`, `gems`, `slag`
  (all referenced by default rules); `slag` added to `config/econ.yaml`.
- `normalize_resource_id` collapses any non-alphanumeric run to a single hyphen.
- Tests rewritten to match the actual API; added `test_rules.py` (tech gating) and
  `test_cli.py` (end-to-end run).
- Generated outputs (`out/`, `.coverage`), Windows `Zone.Identifier` files and the Serena
  cache are no longer tracked.

### Recalibration
- Capacity scales linearly with population (workforce / `labor_required`) instead of
  sqrt(population / 10,000) clamped to 10, and the 1,000-unit cap is gone.
- New `calibration.py`: each rule is scaled so world output of its primary product equals
  world demand x `supply_demand_ratio` (new config field, default 1.0).
- Trade uses net positions: exports are supply minus own demand; imports are demand minus
  own supply. Previously a city could export food it needed itself.
- Loader: baseline agriculture/craftsmanship endowments no longer overwrite higher
  culture-based values (e.g. Noon agriculture 0.8 was reset to 0.5).

### Local industrial mining
- New rules `industrial-iron-mining` and `industrial-coal-mining` (industrial tech,
  `industrial_capacity` endowment) let industrial cities source ore and coal locally,
  without giving them gems/stone/precious metals via `mining_potential`.
- Calibration now computes one factor per resource shared by every rule producing it;
  per-rule factors would have sized each rule to the full demand, doubling supply.
- Industrial cities' needs met locally: `kaupungit` iron ore 0% -> 100%, coal 0% -> 84%
  (iron-ore links 2 -> 5, now exported); `performance_test` iron ore 82% -> 91%, coal
  79% -> 88% (links 497 -> 491 as local mining replaces some imports).

### Steel on kaupungit
- `_extract_endowments` set `industrial_capacity` from a raw `tech` property, which
  `Data/kaupungit.geojson` does not have, so no city could run steel-making. It now uses the
  inferred tech level (explicit `tech` still wins); `performance_test` is unaffected.
- `kaupungit`: 5 steel-making cities; world steel supply 0 -> ~543k (matches demand), and
  calibration raised iron ore to ~3.1M and coal to ~1.1M to cover steel inputs.
- Trade stays at 63 links: the industrial cities are 878+ km apart, and mines are mostly
  elsewhere, so their iron ore and coal needs remain largely unmet.

### Production inputs
- Inputs consumed by production are added to each operator's demand
  (`calculate_input_demand`), so trade exports output minus own consumption minus inputs.
- `calibrate_with_input_demand` sizes each rule for final plus input demand, repeating
  calibration until total demand stops changing (3 passes on `kaupungit`).
- `performance_test`: 304 -> 319 links; coal starts trading (23 links), iron ore 17 -> 41,
  steel 1 -> 3, while stone (37 -> 20) and tools (53 -> 36) are now used locally by
  toolmakers and machinery producers. `kaupungit`: 54 -> 58 links (tools 3 -> 7).
- New extraction rules supply the inputs that had no producer: `seed-cultivation` and
  `fiber-farming` (tribal, agriculture), `precious-metal-mining` and `gem-mining`
  (medieval, mining potential). World supply matches demand for all four; other goods'
  trade is unchanged.
- Seed never trades: it is driven by the same endowment as farming, so farmers grow their
  own. Fiber is grown in 135 `kaupungit` cities but woven in 35, and precious metals/gems
  are mined in only 5 cities for 47 jewelers; distance limits these to 1-2 links each
  there (`performance_test`: fiber 94, precious metals 41, gems 43 links).

### Weapons and armor removed from demand
- Dropped `weapons` from the medieval and industrial demand profiles (code and YAML) and
  `weapons`/`armor` from the plaza, citadel, walls, Night, wildlands and mining modifiers.
- The runtime "Demand profiles reference unknown resources" warning is gone; trade,
  supply and prices are unchanged (weapons were never produced or priced).
- Removed dead weapon/armor/military references from production bonuses (citadel in
  `rules.py` and `capacity.py`, walls, Aumir religion) and the Night culture price
  discount in `pricing.py`. None matched an existing rule or resource; outputs unchanged.
- The walls production bonus matched `stone` in rule IDs, but the stone rule is
  `quarrying`, so it never applied. It now matches `quarrying` (`test_capacity.py`).

### YAML alignment
- `config/econ.yaml` and the built-in defaults now define the same resources, rules,
  demand profiles and simulation settings; `test_config.py` fails if they drift.
- Built-in defaults gained forestry, quarrying, iron-mining and coal-mining (previously
  YAML-only), using the `forestry` and `mining_potential` endowments the loader already set.
  On `kaupungit` this took trade from 43 to 54 links and capped prices from 163 to 0.
- The YAML dropped `weapons` and `weaponsmithing` (removed from defaults in REVISION-001).
- Pricing and trade iterate resources in sorted order, so repeated runs give byte-identical
  data files (previously `prices.json` key order changed between runs).

### Price curve
- The scarcity adjustment in `pricing.py` applied its multiplier twice (roughly squaring
  it), jumped at supply ratios 0.5, 0.8 and 2.0, and went negative above ~9x oversupply.
- Replaced with a constant-elasticity curve: `(demand/supply) ** (1/price_elasticity)`,
  with the supply ratio bounded to [0.05, 20].
- `Data/kaupungit.geojson`: prices at the 10x cap fell from 567/851 to 163/851, and all
  of those were wood, stone and iron-ore, then produced by no default rule. Links importing
  at the cap fell from 73/95 to 0/43.
- Trade on `kaupungit` fell from 95 to 43 links, mostly food (42 -> 4): its cities are a
  median ~470 km apart, and at realistic food prices long-haul grain no longer covers
  transport cost (0.02/km). `transport_cost_per_km` is the main lever: at 0.01, the YAML
  config gives 80 links instead of 59.

## Implementation Status

### ✅ COMPLETED COMPONENTS

#### Core Infrastructure (100% Complete)
- **Data Models** (`models.py`) - Comprehensive Pydantic models with validation
- **Configuration System** - YAML-based configuration with defaults and templates
- **CLI Interface** (`cli.py`) - Full-featured command-line interface with Rich output
- **Logging Framework** - Structured logging throughout all components

#### Data Processing (100% Complete)  
- **GeoJSON Loading** (`io_geojson.py`) - Robust parsing with coordinate transformation
- **Resource Taxonomy** (`taxonomy.py`) - Hierarchical resource classification system
- **Production Rules Engine** (`rules.py`) - DAG-validated production chains
- **Operator Modeling** - Complete geographic and economic entity representation

#### Economic Calculations (75% Complete)
- **Capacity Calculation** (`capacity.py`) - Production capability determination
- **Demand Modeling** (`demand.py`) - Population-based consumption calculation  
- **Price Calculation** (`pricing.py`) - Supply/demand-driven market pricing
- **Spatial Trade Network** (`trade.py`) - Geographic partner discovery and distance calculation

#### Analysis and Reporting (100% Complete)
- **Report Generation** (`report.py`) - Comprehensive markdown analysis reports
- **Data Export** - JSON/JSONL output formats for all major data structures
- **Network Statistics** - Trade flow analysis and economic metrics

### ❌ BROKEN COMPONENTS

#### Supply/Demand Calibration (Resolved)
- **Root Cause:** Production capacity (~1 unit per rule per operator) was orders of
  magnitude below demand (per-capita x population): supply ~3,100 vs. demand ~12.9 million
  units on `Data/kaupungit.geojson`.
- **Fix:** Population-linear capacity plus per-rule calibration (`calibration.py`) and net
  surplus/deficit trading. See "Recalibration" above.

#### Price Curve (Resolved)
- Constant-elasticity curve replaces the step function (see "Price curve" above).

#### Supply Calculation (Resolved)
- `_calculate_supply_from_capacities()` uses rule output resource IDs
  (covered by `test_integration.py`).

### ⚠️ PARTIAL/QUESTIONABLE COMPONENTS

#### Data Integration
- **City Name Extraction:** Logic correct but needs verification
- **Technology Consistency:** Weapons in tribal demand profiles
- **Endowment Inference:** Geographic feature derivation may need tuning

## Testing Status

### Implemented Tests
- **Unit Tests:** Model validation and basic component functionality
- **Integration Tests:** Limited cross-component testing  
- **Data Validation:** GeoJSON parsing and operator creation

### Missing Critical Tests
- **End-to-End Pipeline:** Full simulation workflow validation
- **Supply/Demand Integration:** Resource ID consistency verification
- **Trade Flow Logic:** Profitability calculation and route generation
- **Performance Testing:** Large dataset handling (1000+ operators)

## Performance Characteristics

### Current Capabilities
- **Small Scale (3 operators):** Sub-second processing
- **Medium Scale (140 operators):** ~2-3 seconds processing
- **Memory Usage:** Reasonable for current test sizes
- **Spatial Indexing:** Efficient KDTree-based neighbor queries

### Scalability Concerns
- **Trade Opportunity Matrix:** O(n²) complexity for large networks
- **Memory Growth:** Potentially exponential for dense trade networks
- **Processing Time:** Acceptable for current scale, untested at 1000+ operators

## Data Quality Assessment

### Input Data Quality
- **GeoJSON Structure:** Well-formatted with consistent attribute names
- **Coordinate Systems:** Proper EPSG:3857 to WGS84 transformation
- **Population Data:** Realistic ranges (3K - 79K inhabitants)
- **Geographic Features:** Rich attribute set (elevation, culture, religion, infrastructure)

### Derived Data Quality
- **Technology Inference:** Population-based classification appears reasonable
- **Endowment Derivation:** Geographic feature-based resource availability
- **Infrastructure Mapping:** Comprehensive flag extraction from GeoJSON properties

### Output Data Integrity
- **Operator Creation:** 100% success rate on test data
- **Capacity Calculation:** Produces non-zero values for all applicable operators
- **Demand Profiles:** Technology-appropriate resource requirements (with noted exception)
- **Price Calculation:** Reasonable price ranges based on supply/demand

## Critical Issues Analysis

### Issue #1: Zero Trade Routes (CRITICAL)
**Severity:** Blocks core functionality  
**Confidence:** High - reproduced across multiple test scenarios  
**Investigation Priority:** Highest

**Update 2026-09-30:** The resource ID mismatch described below was fixed earlier, and trade
links appeared - but only because tech levels compared alphabetically, letting tribal
operators run medieval/industrial rules. With that fixed, the remaining cause is the
supply/demand scale mismatch, now resolved by calibration (see "Recalibration" above).
The original analysis is kept below for history.

**Suspected Root Cause:** Resource ID mismatch between components
```python
# Supply calculation creates synthetic IDs
supply["city1"]["toolmaking-output"] = 10.0

# Demand uses taxonomy resource IDs
demand["city2"]["tools"] = 5.0  

# Trade solver finds no common resources
common_resources = {"toolmaking-output"} ∩ {"tools"} = ∅
```

**Verification Required:**
- Audit resource ID generation across all components
- Add diagnostic logging to trade opportunity generation
- Create simple test case with known matching resources

### Issue #2: Technology Consistency (MINOR)
**Severity:** Logical inconsistency, system functions  
**Confidence:** Confirmed in code inspection  
**Investigation Priority:** Low

Weapons resource defined as Medieval tech but may appear in Tribal demand profiles.

### Issue #3: Name Extraction (MINOR)  
**Severity:** Data quality concern, no functional impact  
**Confidence:** Logic appears correct, needs verification  
**Investigation Priority:** Low

## Immediate Action Items

### High Priority (Week 1)
1. **Diagnose Trade Route Failure**
   - Add comprehensive debug logging to `trade.py`
   - Verify resource ID consistency across supply/demand/pricing
   - Create minimal test case with manual data validation

2. **Fix Supply Calculation**
   - Modify `_calculate_supply_from_capacities()` to use rule output resource IDs
   - Ensure consistency with demand calculation resource references

3. **Add Integration Tests**
   - Create end-to-end pipeline test with known expected results
   - Verify supply/demand data structure alignment
   - Test trade flow generation with simplified scenario

### Medium Priority (Week 2-3)
4. **Resource ID Standardization**
   - Audit all components for resource identifier usage
   - Create central resource ID validation utilities
   - Add runtime assertions for data structure consistency

5. **Performance Baseline**
   - Establish performance benchmarks for current working components
   - Profile memory usage patterns
   - Test scaling limits with synthetic data

6. **Documentation Completion**
   - Add comprehensive API documentation
   - Create developer setup guide
   - Document data format specifications

### Low Priority (Week 4+)
7. **Technology Consistency Audit**
   - Review all demand profiles for tech-appropriate resources
   - Consider tribal weapon alternatives
   - Add validation for technology-resource alignment

8. **Enhanced Testing**
   - Property-based testing for economic calculations
   - Stress testing with large datasets
   - Historical scenario validation

9. **User Experience**
   - Improve CLI output formatting
   - Add progress indicators for long-running operations
   - Create sample configuration files

## Success Metrics

### Immediate (Fix Critical Issues)
- [ ] Trade route generation produces non-zero results
- [ ] Supply/demand resource IDs align correctly
- [ ] End-to-end pipeline test passes with expected trade volumes

### Short Term (System Stability)
- [ ] Consistent results across multiple runs with same seed
- [ ] Performance acceptable for 500+ operators
- [ ] Comprehensive test coverage (>80%) for core components

### Long Term (Feature Complete)
- [ ] Economic simulation produces realistic trade patterns
- [ ] Multi-technology scenarios work correctly
- [ ] System handles edge cases gracefully (isolated operators, resource scarcity)

## Development Environment

### Current Setup
- **Python Version:** 3.12+
- **Package Manager:** UV for fast dependency management
- **Code Quality:** Ruff for linting and formatting
- **Testing Framework:** Pytest with coverage reporting
- **CLI Framework:** Typer with Rich for enhanced output

### Development Workflow
```bash
# Development cycle
uv sync                    # Update dependencies
uv run ruff check .       # Code quality check
uv run pytest            # Run test suite  
uv run python -m src.econgen.cli run --input data/test.geojson  # Test run
```

## Risk Assessment

### High Risk
- **Trade Flow Solver:** Core functionality completely broken
- **Resource ID Consistency:** Fundamental architecture issue

### Medium Risk  
- **Performance Scaling:** Untested at production scale
- **Data Quality:** Limited validation of economic realism

### Low Risk
- **Technology Logic:** Minor inconsistencies, system functional
- **User Interface:** Adequate for development, may need polish for production

## Conclusion

The Enonomics system has a robust foundation with excellent code quality, comprehensive configuration options, and well-structured components. The critical trade route generation issue appears to be an integration problem rather than a fundamental architectural flaw. 

**Estimated Time to Working System:** 1-2 weeks focused development  
**Confidence Level:** High - root cause analysis points to fixable integration issues  
**Development Priority:** Fix trade solver before adding new features

The system shows strong potential for achieving its worldbuilding and economic simulation goals once the critical integration issues are resolved.