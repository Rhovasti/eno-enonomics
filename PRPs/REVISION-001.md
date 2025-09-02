# PRP-REVISION-001: Critical System Fixes for Trade Route Generation

## FEATURE:

Fix critical trade route generation system in Enonomics economic simulation. Currently, the system generates 0 trade routes despite having functional supply/demand calculation components due to resource ID mapping inconsistencies between supply and demand systems.

**Primary Objectives:**
1. Fix trade route solver to generate functional trade networks
2. Resolve resource ID mapping inconsistencies across components  
3. Remove inappropriate weapons commodity from tribal technology levels
4. Establish comprehensive integration testing

**Expected Outcome:** Working economic simulation that generates realistic trade routes between geographic entities based on supply/demand dynamics.

## EXAMPLES:

Based on validation testing in `src/econgen/tests/test_validation.py`:

### Current Broken Behavior:
```bash
$ uv run python -m src.econgen.cli run --input data/tiny_world.geojson
Trade Links: 0  # ❌ Should be > 0
Generated 0 potential trade opportunities  # ❌ Root cause identified
```

### Expected Fixed Behavior:
```bash
$ uv run python -m src.econgen.cli run --input data/tiny_world.geojson
Trade Links: 3-5  # ✅ Should show active trade between 3 cities
Generated 12 potential trade opportunities  # ✅ Should find matching supply/demand
```

### Resource ID Mapping Issue (Core Problem):
```python
# Current Broken State:
supply = {"TestCity": {"farming-output": 10.0, "toolmaking-output": 5.0}}  # Synthetic IDs
demand = {"SmallTown": {"food": 8.0, "tools": 3.0}}  # Taxonomy resource IDs  
# Result: No common resources = No trade opportunities

# Target Fixed State:  
supply = {"TestCity": {"food": 10.0, "tools": 5.0}}  # Match taxonomy IDs
demand = {"SmallTown": {"food": 8.0, "tools": 3.0}}  # Taxonomy resource IDs
# Result: Common resources = Trade opportunities generated
```

### Weapons Commodity Issue:
```python
# Current: Weapons appear in tribal demand profiles
tribal_demand = {"weapons": 2.0, "food": 10.0}  # ❌ Inconsistent with tech level

# Target: Remove weapons from tribal/stone age technology  
tribal_demand = {"food": 10.0, "stone": 3.0}  # ✅ Technology-appropriate resources
```

## DOCUMENTATION:

### Critical Files Requiring Changes:
1. **`/root/Eno/Enonomics/src/econgen/cli.py:313-331`** - `_calculate_supply_from_capacities()` method
2. **`/root/Eno/Enonomics/src/econgen/taxonomy.py`** - Remove weapons from default taxonomy  
3. **`/root/Eno/Enonomics/src/econgen/rules.py`** - Remove weaponsmithing rule
4. **`/root/Eno/Enonomics/src/econgen/demand.py`** - Remove weapons from demand profiles

### Reference Documentation:
1. **STATUS.md** - Complete analysis of current system state and issues
2. **ARCHITECTURE.md** - Technical component relationships and data flows
3. **TROUBLESHOOTING.md** - Debugging guide for trade route issues  
4. **README.md** - Updated system overview with known issues

### Validation Tests:
- **`src/econgen/tests/test_validation.py`** - Comprehensive validation suite created by validation-gates agent
- Tests cover trade route establishment, city naming, and weapons commodity detection

### Technical Analysis Sources:
- **Root Cause Analysis:** Resource ID mismatch between supply generation and demand calculation
- **Component Architecture:** All core components functional except trade solver integration
- **Performance Baseline:** System performs well at small/medium scale (3-140 operators)

## OTHER CONSIDERATIONS:

### Development Environment Requirements:
- **Package Manager:** Use UV exclusively for dependency management (`uv add`, `uv run`, etc.)
- **Code Quality:** Must pass `uv run ruff check .` before commits
- **Testing:** All changes require corresponding test updates
- **Line Length:** Max 100 characters (enforced by ruff in pyproject.toml)

### Critical Code Quality Gotchas:
1. **Never update pyproject.toml directly** - Always use `uv add package-name`  
2. **Resource ID Consistency** - Ensure all components use same resource identifier format from taxonomy
3. **Technology Tier Logic** - Validate that resources match appropriate tech levels (tribal, medieval, etc.)
4. **Production Rule Outputs** - Verify output resources map to actual taxonomy resource IDs

### Performance Considerations:
- Current system handles 3-140 operators efficiently  
- Trade opportunity calculation is O(n²) - consider optimization for 1000+ operators
- Memory usage reasonable but untested at large scale
- Spatial indexing (KDTree) performs well for geographic queries

### Testing Strategy:
- **Unit Tests:** Individual component validation (existing, working)
- **Integration Tests:** Cross-component resource ID consistency (CRITICAL - currently missing)
- **End-to-End Tests:** Full simulation pipeline with known expected results (HIGH PRIORITY)  
- **Validation Tests:** Real-world scenario testing with geographic data

### Known Working Components (Don't Break):
- ✅ GeoJSON loading with coordinate transformation
- ✅ Resource taxonomy system and validation  
- ✅ Production rules engine with DAG validation
- ✅ Economic operator modeling and population inference
- ✅ Spatial trade network and distance calculations
- ✅ Price calculation and market dynamics
- ✅ Report generation and data export

### Fix Priority Order:
1. **CRITICAL:** Fix resource ID mapping in supply calculation (`cli.py:313-331`)
2. **HIGH:** Add integration tests for supply/demand alignment  
3. **MEDIUM:** Remove weapons from inappropriate technology tiers
4. **LOW:** Verify city name extraction (likely already working correctly)

### Success Criteria:
- Trade route generation produces non-zero results on test data
- Supply/demand resource IDs align correctly across all components
- Integration tests pass with expected trade volumes
- System maintains current performance characteristics
- All existing functionality remains intact

### AI Assistant Common Mistakes to Avoid:
- Don't create new files unnecessarily - edit existing components
- Don't assume test frameworks - check existing pytest setup
- Don't break existing working components while fixing trade solver
- Don't add features - focus only on fixing identified critical issues
- Maintain consistency with established patterns in codebase (Pydantic models, type hints, etc.)