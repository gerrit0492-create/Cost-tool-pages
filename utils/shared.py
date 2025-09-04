# utils/shared.py
# Centrale helpers + backwards-compat voor oude imports.

from __future__ import annotations

# Probeer te leunen op utils.io (huidige bron van schema's & IO)
try:
    from .io import (
        SCHEMA_MATERIALS,
        SCHEMA_PROCESSES,
        SCHEMA_BOM,
        read_csv_safe,
        paths,
    )
except Exception:  # pragma: no cover
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

# Backwards-compat: oude namen
MATERIALS = SCHEMA_MATERIALS
PROCESSES = SCHEMA_PROCESSES
BOM = SCHEMA_BOM

__all__ = [
    "SCHEMA_MATERIALS", "SCHEMA_PROCESSES", "SCHEMA_BOM",
    "read_csv_safe", "paths",
    "MATERIALS", "PROCESSES", "BOM",
]
