"""Adapter: turn Enonomics' static economic snapshot into a DynamicsInput.

Each stock obeys ``d(stock)/dt = production_rate - consumption_rate * stock``
(plus trade). ``production_rate`` is the supply (units/time); ``consumption_rate``
is the per-capita demand (``demand / population``), a fractional drain (1/time).
This is stable (drain vanishes as stock -> 0) and avoids the runaway-negative
behaviour of using raw population-scaled demand as an absolute rate.

Trade edges (diffusion between neighbouring cities) are seeded from a
``TradeNetwork`` when ``include_trade`` is set, sidestepping Enonomics' fragile
greedy trade *quantity* solver entirely.
"""

from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol

from ..models import Operator
from .state import DynamicsConfig, DynamicsInput, StockSpec, TradeEdge

TRADE_DISTANCE_SCALE_KM = 100.0


class _TradeNetwork(Protocol):
    """Structural type for the trade-network collaborator (avoids importing trade.py)."""

    def find_trade_partners(self, operator_id: str) -> List[str]: ...
    def calculate_distance(self, op1_id: str, op2_id: str) -> Decimal: ...


class _Taxonomy(Protocol):
    """Structural type for the taxonomy (only needs base-price lookup)."""

    def get_base_price(self, resource_id: str) -> Decimal: ...


class _RulesEngine(Protocol):
    """Structural type for the rules engine (only needs the rule table)."""

    @property
    def rules(self) -> Dict[str, Any]: ...


def recipe_input_rates(rules_engine: _RulesEngine) -> Dict[str, Dict[str, float]]:
    """Units of each input consumed per unit produced, per output resource.

    Derived from the production rules (first rule in sorted rule_id order with
    non-empty inputs wins for each output, so the mapping is deterministic).
    Example: ``living-bronze-forging`` {cunu: 1, sap: 1} -> {living-bronze: 1}
    gives ``{"living-bronze": {"cunu": 1.0, "sap": 1.0}}``.

    Returns:
        ``{output_resource: {input_resource: units per unit produced}}``
    """
    result: Dict[str, Dict[str, float]] = {}
    for rule_id in sorted(rules_engine.rules):
        rule = rules_engine.rules[rule_id]
        if not rule.inputs:
            continue
        for resource_id, output_qty in rule.outputs.items():
            if resource_id in result or output_qty <= 0:
                continue
            result[resource_id] = {
                input_id: float(input_qty) / float(output_qty)
                for input_id, input_qty in sorted(rule.inputs.items())
                if input_qty > 0
            }
    return result


def build_dynamics_input(
    operators: List[Operator],
    supply: Dict[str, Dict[str, Decimal]],
    demand: Dict[str, Dict[str, Decimal]],
    config: DynamicsConfig,
    trade_network: Optional[_TradeNetwork] = None,
    taxonomy: Optional[_Taxonomy] = None,
    rules_engine: Optional[_RulesEngine] = None,
) -> DynamicsInput:
    """Map operators + supply/demand into a DynamicsInput of stocks (+ trade).

    Args:
        operators: Enonomics operators (cities).
        supply: ``{operator_id: {resource_id: qty}}`` from the pipeline.
        demand: ``{operator_id: {resource_id: qty}}`` from the pipeline.
        config: Dynamics configuration (filters, rates, trade knobs).
        trade_network: Optional ``TradeNetwork`` used to seed trade edges.
        taxonomy: Optional taxonomy for base prices.
        rules_engine: Optional rules engine; when given, crafted stocks get
            ``input_rates`` so producing them drains the input stocks.

    Returns:
        A DynamicsInput ready for the Minsky model builder.
    """
    city_filter = set(config.cities) if config.cities else None
    resource_filter = set(config.resources) if config.resources else None

    stocks: List[StockSpec] = []
    initials_by_resource: Dict[str, List[float]] = defaultdict(list)
    for op in operators:
        if city_filter is not None and op.operator_id not in city_filter:
            continue
        op_supply = supply.get(op.operator_id, {})
        op_demand = demand.get(op.operator_id, {})
        resource_ids = set(op_supply) | set(op_demand)
        if resource_filter is not None:
            resource_ids &= resource_filter

        for resource_id in sorted(resource_ids):
            production = float(op_supply.get(resource_id, Decimal("0")))
            consumption = _per_capita_rate(
                float(op_demand.get(resource_id, Decimal("0"))), op.population
            )
            if production <= 0 and consumption <= 0:
                continue
            base_price = float(taxonomy.get_base_price(resource_id)) if taxonomy else 1.0
            initial = _initial_stock(production, config)
            initials_by_resource[resource_id].append(initial)
            stocks.append(
                StockSpec(
                    city=op.operator_id,
                    resource=resource_id,
                    initial_stock=initial,
                    production_rate=production,
                    consumption_rate=consumption,
                    base_price=base_price,
                )
            )

    # Scarcity price references the per-resource mean initial stock ("market parity").
    reference_by_resource = {
        resource: (sum(values) / len(values) if values else 1.0)
        for resource, values in initials_by_resource.items()
    }
    stocks = [
        stock.model_copy(update={"price_reference": reference_by_resource[stock.resource]})
        for stock in stocks
    ]

    # Recipe coupling: crafted stocks drain their inputs (same city only, so
    # the builder never wires into a stock that does not exist).
    if rules_engine is not None:
        requirements = recipe_input_rates(rules_engine)
        stock_keys = {(stock.city, stock.resource) for stock in stocks}
        coupled: List[StockSpec] = []
        for stock in stocks:
            rates = requirements.get(stock.resource)
            if not rates:
                coupled.append(stock)
                continue
            inputs = {
                input_id: rate
                for input_id, rate in rates.items()
                if (stock.city, input_id) in stock_keys
            }
            coupled.append(stock.model_copy(update={"input_rates": inputs}))
        stocks = coupled

    trade_edges: List[TradeEdge] = []
    if config.include_trade and trade_network is not None:
        trade_edges = _build_trade_edges(stocks, trade_network, config)

    return DynamicsInput(
        stocks=stocks,
        trade_edges=trade_edges,
        n_steps=config.n_steps,
        seed=config.seed,
    )


def _per_capita_rate(demand_qty: float, population: int) -> float:
    """Per-capita demand as a fractional drain rate (1/time)."""
    if population <= 0:
        return 0.0
    return demand_qty / population


def _initial_stock(production: float, config: DynamicsConfig) -> float:
    """Producers start with a multiple of one step's output; consumers a baseline."""
    if production > 0:
        return production * config.initial_stock_multiplier
    return config.consumer_baseline_stock


def _build_trade_edges(
    stocks: List[StockSpec], trade_network: _TradeNetwork, config: DynamicsConfig
) -> List[TradeEdge]:
    """Build diffusion trade edges between neighbouring cities per resource."""
    cities_by_resource: Dict[str, set] = defaultdict(set)
    for stock in stocks:
        cities_by_resource[stock.resource].add(stock.city)

    edges: List[TradeEdge] = []
    seen = set()
    partner_count: Dict[str, int] = defaultdict(int)
    for resource in sorted(cities_by_resource):
        for city in sorted(cities_by_resource[resource]):
            if partner_count[city] >= config.max_trade_partners:
                continue
            for neighbour in trade_network.find_trade_partners(city):
                if neighbour not in cities_by_resource[resource]:
                    continue
                if partner_count[city] >= config.max_trade_partners:
                    break
                if partner_count[neighbour] >= config.max_trade_partners:
                    continue
                source, dest = (city, neighbour) if city < neighbour else (neighbour, city)
                if (source, dest, resource) in seen:
                    continue
                seen.add((source, dest, resource))
                distance = float(trade_network.calculate_distance(source, dest))
                conductance = config.trade_conductance / (1.0 + distance / TRADE_DISTANCE_SCALE_KM)
                edges.append(
                    TradeEdge(source=source, dest=dest, resource=resource, conductance=conductance)
                )
                partner_count[source] += 1
                partner_count[dest] += 1
    return edges
