# utils/shared.py
# Centrale "shared" helpers + backwards compatibility shims
# zodat oude pages met MATERIALS/PROCESSES/BOM blijven werken.

from __future__ import annotations

# Probeer zoveel mogelijk door te leiden naar utils.io (en andere utils)
try:
    from .io import (
        SCHEMA_MATERIALS,
        SCHEMA_PROCESSES,
        SCHEMA_BOM,
        read_csv_safe,
        paths,
    )
except Exception:  # pragma: no cover
    # Minimalistische no-op fallback zodat imports niet crashen
    SCHEMA_MATERIALS = {}
    SCHEMA_PROCESSES = {}
    SCHEMA_BOM = {}

    def read_csv_safe(*args, **kwargs):
        return None

    def paths():
        from pathlib import Path
        p = Path("data")
        return {
            "root": Path("."),
            "data": p,
            "materials": p / "materials_db.csv",
            "processes": p / "processes_db.csv",
            "bom": p / "bom_template.csv",
        }

# --- Backwards compatibility: oude namen mappen op nieuwe schema's ---
# Oude code deed: from utils.shared import MATERIALS, PROCESSES, BOM
MATERIALS = SCHEMA_MATERIALS
PROCESSES = SCHEMA_PROCESSES
BOM = SCHEMA_BOM

__all__ = [
    # Nieuwe preferente exports
    "SCHEMA_MATERIALS",
    "SCHEMA_PROCESSES",
    "SCHEMA_BOM",
    "read_csv_safe",
    "paths",
    # Backwards compat
    "MATERIALS",
    "PROCESSES",
    "BOM",
]
