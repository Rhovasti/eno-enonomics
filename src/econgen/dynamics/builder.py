"""Build a Minsky stock/flow model with proportional consumption and trade.

Per stock (city, resource)::

    d(stock)/dt = production - consumption_rate * stock
                  + sum(trade_in) - sum(trade_out)

- production: constant inflow (parameter = supply).
- consumption: proportional drain ``consumption_rate * stock`` (rate = per-capita
  demand). Stable: the drain -> 0 as stock -> 0, so stocks never go negative;
  the no-trade steady state is ``production / consumption_rate``.
- price: scarcity variable ``base + base*PRICE_ALPHA * ref/(ref+stock)`` where ref
  is the per-resource mean stock (bounded in [base, base*(1+PRICE_ALPHA)]; below-parity
  stock -> high price). Recorded per step by the runner (recomputed from stock).
- trade edge (A, B): ``flow = conductance * (price_B - price_A)`` (price gradient),
  added to B and taken from A. Low-price surplus cities export to high-price
  deficit cities; self-balancing (export raises the exporter's price).

Wiring mechanics (validated against Minsky's test suite; see memory
``minsky-local-build``): items placed via ``addVariable``/``addOperation`` +
``mouseUp``; stocks made into integrals via ``getItemAt`` + ``addIntegral``
(which also creates the ``IntOp``); connections are coordinate-based
(``mouseDown``/``mouseUp`` on port coords, with ``getItemAt`` to realize
operation ports); values set via ``variableValues[key].init(str)`` and applied at
``constructEquations`` + ``reset``.
"""

from typing import Any

from .state import DynamicsInput, StockSpec, TradeEdge

_COLS = 8
_CELL_W = 700
_CELL_H = 500

# Price = base + base*PRICE_ALPHA * cons_rate/(cons_rate+stock)  in [base, base*(1+PRICE_ALPHA)].
# Bounded so price-gradient trade (flow = conductance*(price_dest-price_source)) stays
# stable; the naive base*rate/(stock+floor) explodes at low stock and destabilizes.
PRICE_ALPHA = 2.0

# Input-availability gate: gate = S_in / (S_in + INPUT_GATE_REF_FRACTION * ref_in).
# ~0.91 at parity and -> 0 as the input depletes, so recipe drains self-limit and
# input stocks never diverge negative. A full-parity fraction would halve crafted
# production everywhere; 0.1 keeps healthy cities at ~full output.
INPUT_GATE_REF_FRACTION = 0.1


def _num(value: float) -> str:
    """Render a float compactly for ``VariableValue.init``."""
    return f"{value:.10g}"


class MinskyModelBuilder:
    """Turn a DynamicsInput into a live stock/flow model on the minsky singleton."""

    def __init__(self, minsky: Any) -> None:
        self.m = minsky
        self.series: dict[str, str] = {}  # "city/resource" -> valueId ":sN"
        self._cell_origin: dict[int, tuple[float, float]] = {}
        self._stock_handle: dict[tuple[str, str], Any] = {}
        self._integrator: dict[tuple[str, str], Any] = {}
        self._production: dict[tuple[str, str], Any] = {}
        self._consumption: dict[tuple[str, str], Any] = {}
        self._price: dict[tuple[str, str], Any] = {}  # scarcity price op per stock
        self._spec_by_key: dict[tuple[str, str], StockSpec] = {}
        self._drains: dict[tuple[str, str], list[Any]] = {}  # input stock <- drain flows

    def build(self, dynamics_input: DynamicsInput) -> None:
        """Create all items/wires, set values, and build the equation DAG."""
        self.m.clearAllMaps(True)
        self.series.clear()
        self._cell_origin.clear()
        self._price.clear()
        self._spec_by_key.clear()
        self._drains.clear()

        for index, spec in enumerate(dynamics_input.stocks):
            self._create_stock(index, spec)

        edge_flows: dict[tuple[str, str, str], Any] = {}
        for index, edge in enumerate(dynamics_input.trade_edges):
            edge_flows[self._edge_key(edge)] = self._create_edge_flow(index, edge)

        # Input coupling before net wiring: it replaces each stock's production
        # with the gated chain and collects the drains its inputs will suffer.
        for index, spec in enumerate(dynamics_input.stocks):
            self._apply_input_coupling(index, spec)

        for index, spec in enumerate(dynamics_input.stocks):
            self._wire_net(index, spec, dynamics_input.trade_edges, edge_flows)

        self.m.constructEquations()

    # -- per-stock construction -------------------------------------------

    def _create_stock(self, index: int, spec: StockSpec) -> None:
        bx, by = self._cell(index)
        self._cell_origin[index] = (bx, by)
        key = (spec.city, spec.resource)

        prod = self._parameter(f"p{index}", bx, by, spec.production_rate)
        rate = self._parameter(f"k{index}", bx, by + 60, spec.consumption_rate)
        stock, integrator = self._integral(f"s{index}", bx + 350, by + 200, spec.initial_stock)

        consumption = self._operation("multiply", bx + 200, by + 200)
        self._wire(rate, 0, consumption, 1)
        self._wire(stock, 0, consumption, 2)

        # Scarcity price: price = base + base*PRICE_ALPHA * ref/(ref+stock), where ref
        # is the per-resource mean stock ("market parity"). Below-parity stock ->
        # high price (bounded). Drives price-gradient trade; recorded by the runner.
        base = self._parameter(f"b{index}", bx, by + 120, spec.base_price)
        scale = self._parameter(f"a{index}", bx, by + 180, spec.base_price * PRICE_ALPHA)
        ref = self._parameter(f"r{index}", bx, by + 240, spec.price_reference)
        denom = self._operation("add", bx + 200, by + 260)  # ref + stock
        self._wire(ref, 0, denom, 1)
        self._wire(stock, 0, denom, 2)
        scarcity = self._operation("divide", bx + 200, by + 320)  # ref / (ref+stock)
        self._wire(ref, 0, scarcity, 1)
        self._wire(denom, 0, scarcity, 2)
        scaled = self._operation("multiply", bx + 200, by + 380)  # scale * scarcity
        self._wire(scale, 0, scaled, 1)
        self._wire(scarcity, 0, scaled, 2)
        price = self._operation("add", bx + 200, by + 440)  # base + scaled
        self._wire(base, 0, price, 1)
        self._wire(scaled, 0, price, 2)

        self._production[key] = prod
        self._consumption[key] = consumption
        self._stock_handle[key] = stock
        self._integrator[key] = integrator
        self._price[key] = price
        self._spec_by_key[key] = spec
        self.series[f"{spec.city}/{spec.resource}"] = f":s{index}"

    def _apply_input_coupling(self, index: int, spec: StockSpec) -> None:
        """Gate production on input availability and collect per-input drains.

        For each input (sorted), production is chained through
        ``gate = S_in / (S_in + INPUT_GATE_REF_FRACTION * ref_in)`` and a drain
        ``gated_production * rate`` is recorded against the input stock, which
        ``_wire_net`` subtracts from that stock's integrator.
        """
        if not spec.input_rates:
            return
        key = (spec.city, spec.resource)
        accumulator = self._production[key]
        bx, by = self._cell_origin[index]
        x = bx - 250  # column left of the stock's own cell
        for k, input_resource in enumerate(sorted(spec.input_rates)):
            in_key = (spec.city, input_resource)
            if in_key not in self._stock_handle:
                continue
            # Minsky reads "_" as a subscript separator and "-" as minus in
            # variable names (variableValues keys then miss the .init), so
            # generated names use plain alphanumerics only.
            in_spec = self._spec_by_key[in_key]
            theta = in_spec.price_reference * INPUT_GATE_REF_FRACTION
            theta_param = self._parameter(f"th{index}i{k}", x, by + 40, theta)
            denom = self._operation("add", x + 100, by + 100)  # S_in + theta
            self._wire(self._stock_handle[in_key], 0, denom, 1)
            self._wire(theta_param, 0, denom, 2)
            gate = self._operation("divide", x + 200, by + 100)  # S_in / (S_in + theta)
            self._wire(self._stock_handle[in_key], 0, gate, 1)
            self._wire(denom, 0, gate, 2)
            gated = self._operation("multiply", x + 100, by + 200)
            self._wire(accumulator, 0, gated, 1)
            self._wire(gate, 0, gated, 2)
            rate_param = self._parameter(
                f"ir{index}i{k}", x, by + 260, spec.input_rates[input_resource]
            )
            drain = self._operation("multiply", x + 200, by + 260)
            self._wire(gated, 0, drain, 1)
            self._wire(rate_param, 0, drain, 2)
            self._drains.setdefault(in_key, []).append(drain)
            accumulator = gated
            x -= 350  # next input column further left
        self._production[key] = accumulator

    def _create_edge_flow(self, index: int, edge: TradeEdge) -> Any:
        """flow = conductance * (price_dest - price_source); returns the flow op.

        Price-gradient trade: a low-price (surplus) source exports to a high-price
        (deficit) dest. The flow feeds the stock integrators (source loses, dest
        gains) in _wire_net; price itself is derived from stock, closing a stable
        feedback loop.
        """
        source_price = self._price[(edge.source, edge.resource)]
        dest_price = self._price[(edge.dest, edge.resource)]
        total_rows = 1  # band sits just below the stock grid
        ex = index * 160
        ey = (len(self._cell_origin) // _COLS + total_rows) * _CELL_H + index * 120

        conductance = self._parameter(f"g{index}", ex, ey, edge.conductance)
        difference = self._operation("subtract", ex + 100, ey)
        self._wire(dest_price, 0, difference, 1)  # price_dest - price_source
        self._wire(source_price, 0, difference, 2)
        flow = self._operation("multiply", ex + 200, ey)
        self._wire(conductance, 0, flow, 1)
        self._wire(difference, 0, flow, 2)
        return flow

    def _wire_net(
        self,
        index: int,
        spec: StockSpec,
        edges: list[TradeEdge],
        edge_flows: dict[tuple[str, str, str], Any],
    ) -> None:
        """Fold production - consumption - drains +/- trade flows into the integrator."""
        key = (spec.city, spec.resource)
        terms = [(self._consumption[key], -1)]
        terms.extend((drain, -1) for drain in self._drains.get(key, []))
        for edge in edges:
            if edge.resource != spec.resource:
                continue
            if edge.source == spec.city:
                terms.append((edge_flows[self._edge_key(edge)], -1))
            elif edge.dest == spec.city:
                terms.append((edge_flows[self._edge_key(edge)], 1))

        accumulator = self._production[key]
        bx, by = self._cell_origin[index]
        chain_x, chain_y = bx + 300, by + 350
        for term, sign in terms:
            optype = "add" if sign > 0 else "subtract"
            op = self._operation(optype, chain_x, chain_y)
            self._wire(accumulator, 0, op, 1)
            self._wire(term, 0, op, 2)
            accumulator = op
            chain_x += 90
        self._wire(accumulator, 0, self._integrator[key], 1)

    # -- low-level helpers ------------------------------------------------

    @staticmethod
    def _edge_key(edge: TradeEdge) -> tuple[str, str, str]:
        return (edge.source, edge.dest, edge.resource)

    @staticmethod
    def _cell(index: int) -> tuple[float, float]:
        col = index % _COLS
        row = index // _COLS
        return col * _CELL_W, row * _CELL_H

    def _parameter(self, name: str, x: float, y: float, value: float) -> Any:
        self.m.canvas.addVariable(name, "parameter")
        self.m.canvas.mouseUp(x, y)
        self.m.variableValues[f":{name}"].init(_num(value))
        return self._last_item()

    def _integral(self, name: str, x: float, y: float, initial: float) -> tuple[Any, Any]:
        self.m.canvas.addVariable(name, "flow")
        self.m.canvas.mouseUp(x, y)
        self.m.canvas.getItemAt(x, y)
        self.m.addIntegral()
        self.m.variableValues[f":{name}"].init(_num(initial))
        # addIntegral converts the flow var to integral (same index) and appends
        # the IntOp; both are the two most-recent items.
        count = len(self.m.model.items())
        return self.m.model.items[count - 2], self.m.model.items[count - 1]

    def _operation(self, optype: str, x: float, y: float) -> Any:
        self.m.canvas.addOperation(optype)
        self.m.canvas.mouseUp(x, y)
        return self._last_item()

    def _last_item(self) -> Any:
        items = self.m.model.items
        return items[len(items) - 1]

    def _wire(self, src: Any, src_port: int, dst: Any, dst_port: int) -> None:
        sx, sy = self._port(src, src_port)
        dx, dy = self._port(dst, dst_port)
        self.m.canvas.mouseDown(sx, sy)
        self.m.canvas.mouseUp(dx, dy)

    def _port(self, item: Any, port: int) -> tuple[float, float]:
        if "Operation:" in (self._attr(item, "classType") or ""):
            self.m.canvas.getItemAt(item.m_x(), item.m_y())
            item = self.m.canvas.item
        return item.portX(port), item.portY(port)

    @staticmethod
    def _attr(item: Any, attr: str) -> Any:
        try:
            return getattr(item, attr)()
        except Exception:  # noqa: BLE001 - probing an optional pyminsky accessor
            return None
