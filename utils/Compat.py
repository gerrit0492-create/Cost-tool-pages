# utils/compat.py
from __future__ import annotations

# Alles re-exporteren vanuit utils.io
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

# Backward-compat aliases die elders in oude code voorkomen
MATERIALS = SCHEMA_MATERIALS
PROCESSES = SCHEMA_PROCESSES
BOM = SCHEMA_BOM

__all__ = [
    # Nieuwe namen
    "SCHEMA_MATERIALS", "SCHEMA_PROCESSES", "SCHEMA_BOM",
    "read_csv_safe", "paths", "load_materials", "load_processes", "load_bom",
    # Oude aliassen
    "MATERIALS", "PROCESSES", "BOM",
]
