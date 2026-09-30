"""Thin client around the pyminsky C++ singleton.

``pyminsky`` is a CPython extension living outside this package (built at
``minsky_root``). It is imported lazily so that importing this module never
requires the extension — only code that actually builds a model does.
"""

import sys
from pathlib import Path
from typing import Any, Optional

from .. import paths


class MinskyUnavailable(RuntimeError):
    """Raised when the pyminsky extension cannot be imported."""


class MinskyClient:
    """Lazy, idempotent handle to the global ``minsky`` singleton.

    The underlying ``minsky`` object is a process-global singleton (one model at
    a time). This wrapper owns the import and lifecycle (new model, save) but
    does not hide the singleton — the builder reads/writes it directly.
    """

    def __init__(self, minsky_root: Optional[str] = None) -> None:
        # Reason: resolve at construction so ENO_MINSKY_ROOT set at runtime applies.
        self.root = minsky_root if minsky_root is not None else paths.minsky_root()
        self._minsky: Any = None

    def connect(self) -> Any:
        """Import pyminsky (once) and return the ``minsky`` singleton."""
        if self._minsky is None:
            if self.root not in sys.path:
                sys.path.insert(0, self.root)
            try:
                import pyminsky  # type: ignore[import-not-found]  # noqa: F401
                from pyminsky import minsky  # type: ignore[import-not-found]
            except Exception as exc:  # pragma: no cover - environment-dependent
                raise MinskyUnavailable(
                    f"Could not import pyminsky from {self.root}. "
                    "Build Minsky and ensure its shared libs are on the linker "
                    "path (see /etc/ld.so.conf.d/minsky.conf + ldconfig)."
                ) from exc
            self._minsky = minsky
        return self._minsky

    def new_model(self) -> None:
        """Clear the singleton so a fresh model can be built."""
        self.connect().clearAllMaps(True)

    def save(self, path: str | Path) -> str:
        """Garbage-collect then save the current model to ``path`` (.mky)."""
        minsky = self.connect()
        path = str(path)
        minsky.garbageCollect()
        minsky.save(path)
        return path
