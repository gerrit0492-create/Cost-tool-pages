# utils/shared.py
from __future__ import annotations

# Re-export vanuit utils.io om oude en nieuwe imports te verenigen
try:
    from .io import (
        SCHEMA_MATERIALS,
        SCHEMA_PROCESSES,
        SCHEMA_BOM,
        read_csv_safe,
        paths,
        load_materials,
        load_processes,
        load_bom,
    )
except Exception:
    # Fallbacks (repo blijft starten, maar zonder data)
    SCHEMA_MATERIALS = {}
    SCHEMA_PROCESSES = {}
    SCHEMA_BOM = {}
    def read_csv_safe(*args, **kwargs): return None
    def paths():
        from pathlib import Path
        d = Path("data")
        return {
            "root": Path("."), "data": d,
            "materials": d / "materials_db.csv",
            "processes": d / "processes_db.csv",
            "bom": d / "bom_template.csv",
        }
    def load_materials(): return None
    def load_processes(): return None
    def load_bom(): return None

# Backward-compat aliases die elders gebruikt worden
MATERIALS = SCHEMA_MATERIALS
PROCESSES = SCHEMA_PROCESSES
BOM = SCHEMA_BOM

__all__ = [
    "SCHEMA_MATERIALS", "SCHEMA_PROCESSES", "SCHEMA_BOM",
    "MATERIALS", "PROCESSES", "BOM",
    "read_csv_safe", "paths",
    "load_materials", "load_processes", "load_bom",
]
