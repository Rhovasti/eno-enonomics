"""Per-citystate dynamic Minsky simulation with long-run drivers (Phase 3).

Each citystate runs from its founding cycle to 998. Three slow drivers reshape the
economy over centuries so cycle 998 differs from cycle 20:

- **Growth**: population P (integral); production & consumption scale with P.
- **Tech progression**: tech level T (integral, rising); a per-flow gate
  ``le(tier_rank, T)`` unlocks medieval/industrial/alchemical production as T rises.
- **Depletion**: each extractive endowment E (integral, declines with extraction);
  production scales with ``E/E0`` -> extractive cities boom then bust.

Per resource::

    d(stock)/dt = production - consumption + conductance*(consumption - stock)
    production  = prod_pc * P * tech_gate * (E/E0 if extractive else 1)
    consumption = cons_pc * P
"""

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ..dynamics.builder import MinskyModelBuilder
from ..dynamics.client import MinskyClient
from ..models import TECH_ORDER
from ..rules import RulesEngine
from ..taxonomy import ResourceTaxonomy
from .parser import CitystateSpec

FINAL_CYCLE = 998

# Tech-progression rate (ranks/cycle) by temporal_state. Dawn industrializes fast;
# stagnant/crisis states barely advance. A tribal city (T0=0) reaches medieval (T=1)
# at ~1/rate cycles, industrial (T=2) at ~2/rate.
TECH_RATE_BY_STATE = {
    "Dawn": 0.005,
    "Day": 0.003,
    "Noon": 0.0015,
    "Dusk": 0.001,
    "Night": 0.0005,
    "Drifters": 0.001,
    "Wildlands": 0.0008,
    "Winds": 0.001,
    "Dwellers": 0.0008,
    "Symbiotic Decline": 0.0003,
    "Autotrophic Founder": 0.001,
}
DEFAULT_TECH_RATE = 0.0015


class CitystateSimConfig(BaseModel):
    growth_scale: float = Field(default=0.04, gt=0)
    trade_conductance: float = Field(default=1.0, gt=0)
    depletion_horizon: float = Field(
        default=400.0, gt=0, description="Deposit size = production x this many cycles."
    )
    max_step: float = Field(default=1.0, gt=0)
    sample_every: int = Field(default=10, ge=1)
    seed: int = 0


class CitystateHistory(BaseModel):
    name: str
    founded_cycle: int
    final_cycle: int = FINAL_CYCLE
    time: List[float]
    population: List[float]
    tech: List[float]
    stocks: Dict[str, List[float]]
    trade: Dict[str, List[float]]
    resources: List[str]
    model_path: Optional[str] = None


def _tech_rank(spec: CitystateSpec) -> int:
    tags_l = {t.lower() for t in spec.tags}
    tech = (
        "industrial"
        if "industrial" in tags_l
        else (
            "tribal"
            if spec.temporal_state
            in ("Drifters", "Wildlands", "Winds", "Dwellers", "Night", "Symbiotic Decline")
            else "medieval"
        )
    )
    return TECH_ORDER[tech]


def _is_depletable(capacity_driver: Optional[str]) -> bool:
    return capacity_driver == "mining_potential" or (
        capacity_driver is not None and capacity_driver.endswith("_deposit")
    )


class PerCityBuilder(MinskyModelBuilder):
    """Single-city dynamic model: growth + tech progression + depletion."""

    def build_dynamic(
        self,
        spec: CitystateSpec,
        supply: Dict,
        demand: Dict,
        taxonomy: ResourceTaxonomy,
        rules_engine: RulesEngine,
        config: CitystateSimConfig,
    ) -> List[str]:
        self.m.clearAllMaps(True)
        self.series.clear()
        self.resource_info: Dict[str, Dict[str, float]] = {}

        pop0 = max(spec.population, 1)
        growth_flow = spec.growth_rate * config.growth_scale * pop0
        t0_rank = _tech_rank(spec)
        tech_rate = TECH_RATE_BY_STATE.get(spec.temporal_state, DEFAULT_TECH_RATE)

        # Shared state: population P (linear growth) and tech level T (rising).
        self._population, pop_intop = self._integral("P", -1600.0, -1600.0, pop0)
        self._wire(self._parameter("gf", -1600.0, -1500.0, growth_flow), 0, pop_intop, 1)
        self._tech, tech_intop = self._integral("T", -1600.0, -1400.0, t0_rank)
        self._wire(self._parameter("tr", -1600.0, -1300.0, tech_rate), 0, tech_intop, 1)
        self._conductance = self._parameter("cond", -1600.0, -1200.0, config.trade_conductance)

        # Per resource: tier rank + extractive classification from producing rules.
        tier_by_resource = self._tier_by_resource(rules_engine)
        extractive_by_resource = self._extractive_by_resource(rules_engine)

        resources: List[str] = []
        for index, resource in enumerate(sorted(set(supply) | set(demand))):
            production_total = float(supply.get(resource, 0))
            consumption_total = float(demand.get(resource, 0))
            if production_total <= 0 and consumption_total <= 0:
                continue
            prod_pc = production_total / pop0
            cons_pc = consumption_total / pop0
            initial = production_total * 10.0 if production_total > 0 else 50.0
            tier_rank = tier_by_resource.get(resource, 0)
            extractive = production_total > 0 and extractive_by_resource.get(resource, False)
            e0 = production_total * config.depletion_horizon if extractive else 0.0
            self._build_resource(
                index, resource, prod_pc, cons_pc, initial, tier_rank, extractive, e0
            )
            resources.append(resource)
            self.resource_info[resource] = {
                "prod_pc": prod_pc,
                "cons_pc": cons_pc,
                "tier_rank": tier_rank,
                "extractive": extractive,
                "e0": e0,
                "index": index,
            }

        self.m.constructEquations()
        return resources

    def _tier_by_resource(self, rules_engine: RulesEngine) -> Dict[str, int]:
        """Min tech rank among rules producing each resource."""
        result: Dict[str, int] = {}
        for rule in rules_engine.rules.values():
            rank = TECH_ORDER[str(rule.tech_min)]
            for resource in rule.outputs:
                if resource not in result or rank < result[resource]:
                    result[resource] = rank
        return result

    def _extractive_by_resource(self, rules_engine: RulesEngine) -> Dict[str, bool]:
        """A resource is extractive if any producing rule mines a finite deposit."""
        result: Dict[str, bool] = {}
        for rule in rules_engine.rules.values():
            if _is_depletable(rule.capacity_driver):
                for resource in rule.outputs:
                    result[resource] = True
        return result

    def _build_resource(
        self,
        index: int,
        resource: str,
        prod_pc: float,
        cons_pc: float,
        initial: float,
        tier_rank: int,
        extractive: bool,
        e0: float,
    ) -> None:
        bx, by = self._cell(index)
        pp = self._parameter(f"pp{index}", bx, by, prod_pc)
        cp = self._parameter(f"cp{index}", bx, by + 40, cons_pc)
        stock, integrator = self._integral(f"s{index}", bx + 400, by + 120, initial)

        # base production = prod_pc * P
        base = self._operation("multiply", bx + 150, by + 20)
        self._wire(pp, 0, base, 1)
        self._wire(self._population, 0, base, 2)

        # tech gate = le(tier_rank, T)  -> 1 when tech has reached the rule's tier
        gate = self._operation("le", bx + 150, by + 80)
        self._wire(self._parameter(f"tr{index}", bx, by + 80, tier_rank), 0, gate, 1)
        self._wire(self._tech, 0, gate, 2)
        gated = self._operation("multiply", bx + 150, by + 140)
        self._wire(base, 0, gated, 1)
        self._wire(gate, 0, gated, 2)

        # depletion: extractive resources scale with E/E0
        if extractive:
            e_stock, e_intop = self._integral(f"e{index}", bx + 280, by + 200, e0)
            e0_param = self._parameter(f"e0{index}", bx, by + 200, e0)
            dep_factor = self._operation("divide", bx + 280, by + 260)
            self._wire(e_stock, 0, dep_factor, 1)
            self._wire(e0_param, 0, dep_factor, 2)
            production = self._operation("multiply", bx + 150, by + 200)
            self._wire(gated, 0, production, 1)
            self._wire(dep_factor, 0, production, 2)
            # dE/dt = -production  (depletion_rate = 1; deposit shrinks by extraction)
            neg_prod = self._operation("multiply", bx + 280, by + 320)
            self._wire(self._parameter(f"dn{index}", bx, by + 320, -1.0), 0, neg_prod, 1)
            self._wire(production, 0, neg_prod, 2)
            self._wire(neg_prod, 0, e_intop, 1)
        else:
            production = gated

        # consumption = cons_pc * P
        consumption = self._operation("multiply", bx + 150, by + 260)
        self._wire(cp, 0, consumption, 1)
        self._wire(self._population, 0, consumption, 2)

        # trade = conductance * (consumption - stock)
        deficit = self._operation("subtract", bx + 150, by + 320)
        self._wire(consumption, 0, deficit, 1)
        self._wire(stock, 0, deficit, 2)
        trade = self._operation("multiply", bx + 150, by + 380)
        self._wire(self._conductance, 0, trade, 1)
        self._wire(deficit, 0, trade, 2)

        # net = production - consumption + trade -> stock integrator
        n1 = self._operation("subtract", bx + 400, by + 40)
        self._wire(production, 0, n1, 1)
        self._wire(consumption, 0, n1, 2)
        net = self._operation("add", bx + 400, by + 100)
        self._wire(n1, 0, net, 1)
        self._wire(trade, 0, net, 2)
        self._wire(net, 0, integrator, 1)

        self.series[resource] = f":s{index}"


def simulate_city(
    client: MinskyClient,
    spec: CitystateSpec,
    supply: Dict,
    demand: Dict,
    taxonomy: ResourceTaxonomy,
    rules_engine: RulesEngine,
    config: CitystateSimConfig,
) -> CitystateHistory:
    """Build + integrate one city's model from founding to 998; return its history."""
    minsky = client.connect()
    client.new_model()

    builder = PerCityBuilder(minsky)
    resources = builder.build_dynamic(spec, supply, demand, taxonomy, rules_engine, config)

    run_cycles = FINAL_CYCLE - spec.founded_cycle
    minsky.running(True)
    minsky.srand(config.seed)
    minsky.reset()
    try:
        minsky.stepMax(config.max_step)
    except Exception:
        pass

    def _record() -> None:
        time.append(float(minsky.t()))
        population.append(float(minsky.variableValues[":P"].value()))
        tech.append(float(minsky.variableValues[":T"].value()))
        for r in resources:
            info = builder.resource_info[r]
            pop = population[-1]
            t_level = tech[-1]
            stock_val = float(minsky.variableValues[builder.series[r]].value())
            gate = 1.0 if t_level >= info["tier_rank"] else 0.0
            dep = 1.0
            if info["extractive"]:
                e_val = float(minsky.variableValues[f":e{info['index']}"].value())
                dep = e_val / info["e0"] if info["e0"] > 0 else 1.0
            production = info["prod_pc"] * pop * gate * dep
            consumption = info["cons_pc"] * pop
            stocks[r].append(stock_val)
            trade[r].append(config.trade_conductance * (consumption - stock_val))
            production_map[r].append(production)

    time: List[float] = []
    population: List[float] = []
    tech: List[float] = []
    stocks: Dict[str, List[float]] = {r: [] for r in resources}
    trade: Dict[str, List[float]] = {r: [] for r in resources}
    production_map: Dict[str, List[float]] = {r: [] for r in resources}

    _record()  # initial state at t=0
    step = 0
    while minsky.t() < run_cycles:
        minsky.step()
        step += 1
        if step % config.sample_every == 0:
            _record()

    return CitystateHistory(
        name=spec.name,
        founded_cycle=spec.founded_cycle,
        time=time,
        population=population,
        tech=tech,
        stocks=stocks,
        trade=trade,
        resources=resources,
    )


def save_history(history: CitystateHistory, output_dir: Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{history.name}.json").write_text(history.model_dump_json(indent=2))


__all__ = [
    "CitystateSimConfig",
    "CitystateHistory",
    "PerCityBuilder",
    "simulate_city",
    "save_history",
]
