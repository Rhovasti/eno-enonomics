"""Per-citystate long-run economic simulation + cycle-998 profiles.

Phase 1: parser + endowment inference. Later phases add the Minsky per-city
simulator, market price-taker trade, profile generation, and long-run drivers.
"""

from .endowments import infer_endowments
from .parser import CitystateSpec, load_citystates, parse_citystate

__all__ = ["CitystateSpec", "parse_citystate", "load_citystates", "infer_endowments"]
