from __future__ import annotations

try:
    from .io import SCHEMA_MATERIALS, SCHEMA_PROCESSES, SCHEMA_BOM, read_csv_safe, paths
except Exception:
    SCHEMA_MATERIALS, SCHEMA_PROCESSES, SCHEMA_BOM = {}, {}, {}
    def read_csv_safe(*a, **k): return None
    def paths():
        from pathlib import Path
        d = Path('data')
        return {
            'root': Path('.'), 'data': d,
            'materials': d/'materials_db.csv',
            'processes': d/'processes_db.csv',
            'bom': d/'bom_template.csv',
        }

MATERIALS = SCHEMA_MATERIALS
PROCESSES = SCHEMA_PROCESSES
BOM = SCHEMA_BOM

__all__ = [
    'SCHEMA_MATERIALS','SCHEMA_PROCESSES','SCHEMA_BOM',
    'read_csv_safe','paths','MATERIALS','PROCESSES','BOM',
]
