"""Pydantic data models for the Minsky dynamics layer.

These are pure data structures with no Minsky dependency, so they are easy to
construct and test without importing the C++ extension. The adapter turns
Enonomics' static economic snapshot into a ``DynamicsInput``; the builder turns
a ``DynamicsInput`` into a live Minsky model.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DynamicsConfig(BaseModel):
    """Configuration for the dynamic-simulation step (YAML ``dynamics:`` key)."""

    model_config = ConfigDict(use_enum_values=True)

    minsky_root: str = Field(default="/root/minsky", description="Path to the built minsky tree.")
    n_steps: int = Field(default=50, ge=1, description="Number of integration steps to run.")
    seed: Optional[int] = Field(default=None, description="RNG seed for repeatable runs.")
    resources: Optional[List[str]] = Field(
        default=None, description="Restrict simulation to these resource ids (None = all)."
    )
    cities: Optional[List[str]] = Field(
        default=None, description="Restrict simulation to these operator ids (None = all)."
    )
    initial_stock_multiplier: float = Field(
        default=10.0,
        gt=0,
        description="Initial stock = production_rate * this (keeps stocks from "
        "depleting in the first step).",
    )
    include_trade: bool = Field(
        default=False,
        description="Wire inter-city diffusion trade edges between neighboring stocks.",
    )
    consumer_baseline_stock: float = Field(
        default=50.0,
        ge=0,
        description="Initial inventory for consumer-only cities (no production), "
        "so trade has something to act on.",
    )
    trade_conductance: float = Field(
        default=2.0,
        gt=0,
        description="Base trade conductance; actual = this / (1 + distance_km/100). "
        "Recalibrated for price-driven trade (price diffs are O(base), vs the "
        "~100s stock diffs of the old diffusion model); 2.0 sustains consumers "
        "for well-produced resources while letting scarce ones spike.",
    )
    max_trade_partners: int = Field(
        default=3,
        ge=0,
        le=20,
        description="Cap on trade edges per city per resource (keeps model size tractable).",
    )


class StockSpec(BaseModel):
    """One resource stock for one city.

    The stock obeys::

        d(stock)/dt = production_rate - consumption_rate * stock (+ trade)

    where ``production_rate`` is a constant inflow (supply, units/time) and
    ``consumption_rate`` is a fractional drain (1/time, e.g. per-capita demand).
    Proportional drain is stable: it -> 0 as stock -> 0, so stocks never go
    negative, and the no-trade steady state is ``production_rate / consumption_rate``.
    """

    city: str
    resource: str
    initial_stock: float = Field(ge=0)
    production_rate: float = Field(ge=0)
    consumption_rate: float = Field(ge=0)
    base_price: float = Field(
        default=1.0, gt=0, description="Base price for the scarcity price variable."
    )
    price_reference: float = Field(
        default=1.0,
        gt=0,
        description="Reference stock (per-resource mean) for the scarcity price: ref/(ref+stock).",
    )


class TradeEdge(BaseModel):
    """A diffusion trade channel between two city stocks of the same resource.

    Flow = ``conductance * (stock_source - stock_dest)``, added to the dest and
    taken from the source. Redistributes surplus from producers to consumers.
    """

    source: str
    dest: str
    resource: str
    conductance: float = Field(gt=0)


class DynamicsInput(BaseModel):
    """The full specification handed to the Minsky model builder."""

    stocks: List[StockSpec] = Field(default_factory=list)
    trade_edges: List[TradeEdge] = Field(default_factory=list)
    n_steps: int = Field(default=50, ge=1)
    seed: Optional[int] = None


class SimulationResult(BaseModel):
    """Time-series output of a simulation run."""

    time: List[float]
    series: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="Friendly name ('city/resource') -> stock values, one per step.",
    )
    prices: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="Friendly name ('city/resource') -> price values, one per step.",
    )
    n_steps: int
    model_path: Optional[str] = None


__all__ = [
    "DynamicsConfig",
    "StockSpec",
    "TradeEdge",
    "DynamicsInput",
    "SimulationResult",
]
