"""Locations of external resources, overridable with environment variables.

The Minsky build and the Eno-Worldbuilder2 data live outside this repository.
Their defaults match the original development machine; set the environment
variables below to point elsewhere.
"""

import os
from pathlib import Path

ENV_MINSKY_ROOT = "ENO_MINSKY_ROOT"
ENV_CITYSTATES_DIR = "ENO_CITYSTATES_DIR"
ENV_WORLDBUILDER_DIR = "ENO_WORLDBUILDER_DIR"

DEFAULT_MINSKY_ROOT = "/root/minsky"
DEFAULT_WORLDBUILDER_DIR = "/root/Eno/Eno-Worldbuilder2"
DEFAULT_CITYSTATES_DIR = f"{DEFAULT_WORLDBUILDER_DIR}/citystates for economic profiles"


def minsky_root() -> str:
    """Path to the built Minsky tree (``pyminsky`` extension), from ENO_MINSKY_ROOT."""
    return os.environ.get(ENV_MINSKY_ROOT, DEFAULT_MINSKY_ROOT)


def citystates_dir() -> Path:
    """Directory of citystate ``.md`` profiles, from ENO_CITYSTATES_DIR."""
    return Path(os.environ.get(ENV_CITYSTATES_DIR, DEFAULT_CITYSTATES_DIR))


def worldbuilder_dir() -> Path:
    """Root of the Eno-Worldbuilder2 checkout (GIS data), from ENO_WORLDBUILDER_DIR."""
    return Path(os.environ.get(ENV_WORLDBUILDER_DIR, DEFAULT_WORLDBUILDER_DIR))


__all__ = [
    "ENV_MINSKY_ROOT",
    "ENV_CITYSTATES_DIR",
    "ENV_WORLDBUILDER_DIR",
    "DEFAULT_MINSKY_ROOT",
    "DEFAULT_CITYSTATES_DIR",
    "DEFAULT_WORLDBUILDER_DIR",
    "minsky_root",
    "citystates_dir",
    "worldbuilder_dir",
]
