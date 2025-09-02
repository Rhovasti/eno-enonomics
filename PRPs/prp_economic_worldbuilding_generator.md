# Base PRP Template v2 – Context‑Rich with Validation Loops (Filled)

> **Feature**: Economic Worldbuilding Generator for Python-based worldbuilding scripts
>
> **Scope**: Parse GeoJSON entities (cities, organizations, buildings, districts, people) → infer economic operators → assign tech level → attach resources & capabilities → build production chains → compute local outputs, inter-city trade flows, and scarcity/advantage scores → emit machine-usable JSON/CSV + human docs.

---

## Goal
Build a deterministic, data‑driven **Economic Worldbuilding Generator** that:
1. Reads project GeoJSON files (≈140 cities + organizations, buildings, districts, people).
2. Identifies **economic operators** and attaches **technological levels** (Tribal, Medieval, Industrial).
3. Models **resources** (raw → refined → advanced goods) with expandable **production rules** and **multi‑input chains**.
4. Computes **local production capacity**, **consumption demand**, **specialization**, and **inter‑city trade** (distance/friction aware).
5. Outputs: structured datasets (JSON/CSV/Parquet) + a concise human‑readable report.

## Why
- **Believability**: Ground worldbuilding in consistent, geography‑aware economics.
- **Tooling**: Create reproducible outputs that downstream scripts (population, logistics, narrative hooks) can consume.
- **Scalability**: Support hundreds of entities with controllable complexity.

## What (User-visible behavior & technical requirements)
- CLI command `econgen run --input data/geo/*.geojson --config config/econ.yaml --out out/econ/`.
- Deterministic by default; `--seed` enables pseudo‑random variation (bounds respected by config).
- Produces:
  - `operators.jsonl` (one per operator with tech level, resources, capacity)
  - `production_edges.jsonl` (input→output rules instantiated per operator)
  - `trade_links.jsonl` (pairwise trade with quantities, price deltas, routes)
  - `econ_report.md` (summary: top producers, bottlenecks, scarcity, outliers)
- Validates GeoJSON schema and reports missing/ambiguous fields with actionable messages.

### Success Criteria
- [ ] End‑to‑end run completes on 140+ entities in < 60s on a typical laptop (configurable; provide benchmark script).
- [ ] Deterministic outputs without `--seed` given identical inputs.
- [ ] All resources and chains defined in config are represented in outputs or explained as infeasible.
- [ ] Unit tests ≥ 30, coverage ≥ 85% for core modules.
- [ ] Lint/type checks pass (ruff/mypy), CI green.

---

## All Needed Context

### Documentation & References
```yaml
- file: INITIAL.md
  why: High‑level feature framing and examples

- file: prp_base.md
  why: PRP methodology (validation loops, structure, anti‑patterns)

- file: data/README.md
  why: GeoJSON field dictionary (ids, names, coords, categories, optional tech hints)

- docfile: PRPs/econ/resources.md
  why: Canonical resource taxonomy & example chains (raw→refined→advanced)

- docfile: PRPs/econ/config_spec.md
  why: Config schema for tech levels, production rules, demand profiles, friction
```

### Current Codebase tree (fill when known)
```bash
.
├── INITIAL.md
├── prp_base.md
├── src/
│   └── (to be created)
├── config/
│   └── (to be created)
└── tests/
    └── (to be created)
```

### Desired Codebase tree
```bash
.
├── INITIAL.md
├── prp_base.md
├── config/
│   ├── econ.yaml                      # Main config: tech levels, resources, rules
│   ├── resources.yaml                 # Optional split: resource taxonomy
│   └── demand_profiles.yaml           # Consumption per capita by tech level
├── src/econgen/
│   ├── __init__.py
│   ├── cli.py                         # Typer/argparse CLI
│   ├── io_geojson.py                  # Load/validate GeoJSON entities
│   ├── models.py                      # Pydantic models (Operator, Resource, Rule, TradeLink)
│   ├── taxonomy.py                    # Resource taxonomy & tech gates
│   ├── rules.py                       # Production rules engine
│   ├── capacity.py                    # Capacity estimation per operator
│   ├── demand.py                      # Demand estimation per operator/tech
│   ├── trade.py                       # Trade network construction and flow solve
│   ├── pricing.py                     # Simple price model (scarcity/transport)
│   ├── report.py                      # Markdown summary
│   └── util.py                        # Determinism, distance, graph helpers
├── examples/
│   ├── cities_sample.geojson
│   └── minimal_config.yaml
├── tests/
│   ├── test_taxonomy.py
│   ├── test_rules.py
│   ├── test_capacity.py
│   ├── test_demand.py
│   ├── test_trade.py
│   ├── test_io_geojson.py
│   └── data/
│       └── tiny_world.geojson
└── out/ (generated)
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: Keep resource & rule IDs machine-safe (lowercase, hyphenated).
# GeoJSON may include mixed geometry types; we only need centroids for distance.
# Avoid circular production chains: detect via DAG check; fail fast with location hint.
# Determinism: seed numpy/random in one place; avoid unordered set/dict iteration in outputs.
# Performance: N^2 trade candidates prunes via radius/degree caps; use KDTree for nearest.
# Units: Distances in km; capacities per time-step (configurable), price in abstract credits.
```

---

## Implementation Blueprint

### Data Models and Structure (Pydantic v2 style)
```python
from pydantic import BaseModel, Field
from typing import Dict, List, Tuple, Optional

class TechLevel(str):
    # 'tribal' | 'medieval' | 'industrial'
    pass

class Resource(BaseModel):
    id: str
    tier: int  # 0=raw, 1=refined, 2=advanced, ...
    tech_min: TechLevel  # minimum tech level that can exploit/produce

class ProductionRule(BaseModel):
    id: str
    inputs: Dict[str, float]       # resource_id -> qty
    outputs: Dict[str, float]
    tech_min: TechLevel
    byproducts: Dict[str, float] = {}
    capacity_driver: Optional[str] = None  # e.g., 'iron_ore', 'forest', 'population'

class Operator(BaseModel):
    id: str
    name: str
    kind: str  # city|org|building|district|person
    tech: TechLevel
    coord: Tuple[float, float]
    tags: List[str] = []           # e.g., 'port', 'mine', 'university'
    endowments: Dict[str, float] = {}  # resource stocks (e.g., deposits, arable land index)

class Capacity(BaseModel):
    operator_id: str
    rule_id: str
    max_rate: float  # per time-step

class DemandProfile(BaseModel):
    tech: TechLevel
    per_capita: Dict[str, float]  # resource_id -> qty

class TradeLink(BaseModel):
    src: str
    dst: str
    resource: str
    qty: float
    distance_km: float
    price_src: float
    price_dst: float
```

### Resource Taxonomy & Tech Gates (config example)
```yaml
tech_levels: [tribal, medieval, industrial]

resources:
  - {id: wood, tier: 0, tech_min: tribal}
  - {id: stone, tier: 0, tech_min: tribal}
  - {id: hides, tier: 0, tech_min: tribal}
  - {id: iron_ore, tier: 0, tech_min: medieval}
  - {id: grain, tier: 0, tech_min: tribal}
  - {id: wool, tier: 0, tech_min: tribal}
  - {id: coal, tier: 0, tech_min: industrial}
  - {id: steel, tier: 1, tech_min: industrial}
  - {id: tools, tier: 1, tech_min: medieval}
  - {id: cloth, tier: 1, tech_min: medieval}
  - {id: bread, tier: 1, tech_min: medieval}
  - {id: chemicals, tier: 1, tech_min: industrial}
  - {id: locomotive, tier: 2, tech_min: industrial}

rules:
  - id: carpentry
    tech_min: tribal
    inputs:  {wood: 2}
    outputs: {tools: 1}
    capacity_driver: forest_index

  - id: blacksmithing
    tech_min: medieval
    inputs:  {iron_ore: 3, wood: 1}
    outputs: {tools: 2}

  - id: milling
    tech_min: medieval
    inputs:  {grain: 3}
    outputs: {bread: 2}

  - id: weaving
    tech_min: medieval
    inputs:  {wool: 2}
    outputs: {cloth: 1}

  - id: steelmaking
    tech_min: industrial
    inputs:  {iron_ore: 3, coal: 2}
    outputs: {steel: 2}

  - id: locomotive_works
    tech_min: industrial
    inputs:  {steel: 10, tools: 2, chemicals: 1}
    outputs: {locomotive: 1}

pricing:
  base: {wood: 1, stone: 1, hides: 2, iron_ore: 3, grain: 1, wool: 2, coal: 2, steel: 8, tools: 5, cloth: 6, bread: 2, chemicals: 7, locomotive: 100}
  transport_cost_per_km: 0.02  # additive per unit
  scarcity_multiplier: true

trade:
  max_neighbors: 8
  max_radius_km: 800
  min_trade_qty: 0.5
```

### GeoJSON Expectations (minimal fields)
```json
{
  "type": "Feature",
  "properties": {
    "id": "city-001",
    "name": "Astra",
    "kind": "city",
    "tech": "medieval",          // optional hint; else infer from tags/pop/history
    "tags": ["port", "market"],
    "population": 24000,
    "endowments": {"forest_index": 0.8, "arable_index": 0.6, "iron_ore": 0.2}
  },
  "geometry": { "type": "Point", "coordinates": [24.94, 60.17] }
}
```

---

## List of Tasks (in order)

```yaml
Task 1: Bootstrap
CREATE src/econgen/cli.py:
  - Implement CLI with commands: run, validate, report
  - Flags: --input (glob), --config, --out, --seed, --strict

CREATE src/econgen/io_geojson.py:
  - Load features, coerce to Operators, compute centroids
  - Validate required fields; log/warn defaults

Task 2: Taxonomy & Config
CREATE src/econgen/taxonomy.py:
  - Load resources & tech levels from YAML
  - Provide lookup helpers and validation

Task 3: Rules Engine
CREATE src/econgen/rules.py:
  - Load ProductionRule set from config
  - Validate tech gates and resource IDs; DAG cycle check

Task 4: Capacity Estimation
CREATE src/econgen/capacity.py:
  - For each operator and eligible rule, compute max_rate from endowments/pop
  - Deterministic scaling; clamp to config bounds

Task 5: Demand Profiles
CREATE src/econgen/demand.py:
  - Per tech level, per-capita demand; multiply by population (or operator scale)
  - Output demand vector per operator

Task 6: Local Balance & Pricing
CREATE src/econgen/pricing.py:
  - Compute local supply/demand surplus; price via base * scarcity factor

Task 7: Trade Network
CREATE src/econgen/trade.py:
  - Build KDTree; candidate links by radius/degree
  - Move goods from low price to high price up to capacity; include transport cost
  - Output TradeLink records

Task 8: Reporting
CREATE src/econgen/report.py:
  - Summaries (top producers, chokepoints, unmet demand, outliers)
  - Render to Markdown

Task 9: CLI Integration
MODIFY src/econgen/cli.py:
  - Wire pipeline run -> emit operators.jsonl, production_edges.jsonl, trade_links.jsonl, econ_report.md

Task 10: Tests & CI
CREATE tests/* with fixtures and ≥30 tests
  - Include tiny_world.geojson and minimal_config.yaml
```

### Per-Task Pseudocode (selected)
```python
# io_geojson.load_operators(paths)
features = read_all(paths)
ops = []
for f in features:
    props = f["properties"]
    lon, lat = centroid(f["geometry"])  # ok for points/polygons
    op = Operator(
        id=props.get("id") or slugify(props["name"]),
        name=props["name"],
        kind=props.get("kind", "city"),
        tech=infer_tech(props),
        coord=(lat, lon),
        tags=props.get("tags", []),
        endowments=props.get("endowments", {}),
    )
    ops.append(op)
return ops

# rules.instantiate_for_operator(op)
eligible = [r for r in rules if op.tech >= r.tech_min]
for r in eligible:
    if all(req in taxonomy.resources for req in r.inputs):
        yield r

# capacity.estimate(op, rule)
base = 1.0
if rule.capacity_driver and rule.capacity_driver in op.endowments:
    base *= scale(op.endowments[rule.capacity_driver])
if op.population:
    base *= labor_scale(op.population)
return clamp(base, min_cap, max_cap)

# trade.solve(ops, prices, supply, demand)
# Build neighbor graph (KDTree) and greedy flow from cheap->expensive while qty>min, obeying transport costs
```

### Integration Points
```yaml
CONFIG:
  - Add/maintain config/econ.yaml and friends; keep IDs stable.
CLI:
  - Add entry-point: `python -m src.econgen.cli` or `econgen` via console_scripts.
DATA:
  - Accept multiple GeoJSONs; merge by operator id.
OUTPUTS:
  - JSONL files under out/econ/; include schema version in header file.
```

---

## Validation Loop

### Level 1: Syntax & Style
```bash
ruff check src/ --fix
mypy src/
```

### Level 2: Unit Tests
```python
# tests/test_taxonomy.py
def test_load_resources_validates_ids(): ...

# tests/test_rules.py
def test_cycle_detection_raises(): ...

# tests/test_capacity.py
def test_capacity_scales_with_endowment(): ...

# tests/test_demand.py
def test_demand_by_tech_level(): ...

# tests/test_trade.py
def test_trade_respects_transport_costs(): ...

# tests/test_io_geojson.py
def test_geojson_to_operator_defaults(): ...
```

```bash
pytest -q
```

### Level 3: Integration Test
```bash
python -m src.econgen.cli run \
  --input tests/data/tiny_world.geojson \
  --config examples/minimal_config.yaml \
  --out out/e2e --seed 42

# Expect: files emitted + report contains all operators and at least one trade link
```

### Final Validation Checklist
- [ ] All tests pass (`pytest`)
- [ ] No lint/type errors (`ruff`, `mypy`)
- [ ] E2E run emits expected artifacts
- [ ] Report highlights top producers & bottlenecks
- [ ] Deterministic outputs without `--seed`

---

## Anti‑Patterns to Avoid
- ❌ Ad‑hoc resource names or mixed casing (breaks joins)
- ❌ Hidden randomness; always seed it
- ❌ Implicit unit changes (km vs. degrees)
- ❌ Silently dropping infeasible rules; report them
- ❌ O(N²) trade without pruning

---

## Appendices

### A. Minimal `examples/minimal_config.yaml`
```yaml
include: [config/resources.yaml, config/demand_profiles.yaml]
transport_cost_per_km: 0.02
max_neighbors: 8
max_radius_km: 800
min_trade_qty: 0.5
```

### B. Demand Profiles (example)
```yaml
tribal:
  per_capita: {bread: 0.2, tools: 0.05, cloth: 0.03}
medieval:
  per_capita: {bread: 0.5, tools: 0.1, cloth: 0.1}
industrial:
  per_capita: {bread: 0.6, tools: 0.2, cloth: 0.2, chemicals: 0.05}
```

### C. Example Tiny World (tests/data/tiny_world.geojson)
```json
{"type":"FeatureCollection","features":[
  {"type":"Feature","properties":{"id":"city-a","name":"A","kind":"city","tech":"medieval","population":12000,"endowments":{"forest_index":0.7,"iron_ore":0.4,"arable_index":0.5}},"geometry":{"type":"Point","coordinates":[24.94,60.17]}},
  {"type":"Feature","properties":{"id":"city-b","name":"B","kind":"city","tech":"industrial","population":38000,"endowments":{"coal":0.6,"arable_index":0.4}},"geometry":{"type":"Point","coordinates":[25.01,60.20]}}
]}
```

---

**Next actions**
1. Confirm GeoJSON field names you already use (e.g., `nim` for city name?) and mapping → `name`/`id`.
2. Approve/adjust resource taxonomy & production rules starter set.
3. I’ll generate the initial code scaffolding (CLI + loaders + config schema + 5 base tests).

