"""Dynamic time-evolution layer: simulate Enonomics worlds forward in Minsky.

Pipeline: Enonomics snapshot -> ``build_dynamics_input`` -> ``simulate`` (builds
a Minsky stock/flow model, integrates it, samples series) -> ``write_outputs``.
"""

from .adapter import build_dynamics_input
from .client import MinskyClient, MinskyUnavailable
from .runner import simulate, write_outputs
from .state import (
    DynamicsConfig,
    DynamicsInput,
    SimulationResult,
    StockSpec,
    TradeEdge,
)

__all__ = [
    "DynamicsConfig",
    "DynamicsInput",
    "MinskyClient",
    "MinskyUnavailable",
    "SimulationResult",
    "StockSpec",
    "TradeEdge",
    "build_dynamics_input",
    "simulate",
    "write_outputs",
]
