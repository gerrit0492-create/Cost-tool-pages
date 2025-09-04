# utils/io.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd

# --- Schéma’s (houd dit simpel; breid uit naar wens) ---
SCHEMA_MATERIALS: Dict[str, Any] = {
    "material_id": "string",
    "description": "string",
    "price_eur_per_kg": "float64",
}
SCHEMA_PROCESSES: Dict[str, Any] = {
    "process_id": "string",
    "machine_rate_eur_h": "float64",
    "labor_rate_eur_h": "float64",
    "overhead_pct": "float64",
    "margin_pct": "float64",
}
SCHEMA_BOM: Dict[str, Any] = {
    "material_id": "string",
    "qty": "Int64",
    "mass_kg": "float64",
    "process_route": "string",
    "runtime_h": "float64",
}

# --- Paden ---
def paths() -> Dict[str, Path]:
    d = Path("data")
    return {
        "root": Path("."),
        "data": d,
        "materials": d / "materials_db.csv",
        "processes": d / "processes_db.csv",
        "bom": d / "bom_template.csv",
    }

# --- Helpers ---
def _dtype_map(schema: Dict[str, Any]) -> Dict[str, Any]:
    # pandas dtypes als mapping: strings laten we door, floats/Int64 ook
    return {k: v for k, v in schema.items()}

def read_csv_safe(path: Path, schema: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    if schema is None:
        return pd.read_csv(path)
    dtypes = _dtype_map(schema)
    df = pd.read_csv(path, dtype={k: v for k, v in dtypes.items() if v != "Int64"})
    # pandas 'Int64' (nullable) apart toepassen
    for col, typ in dtypes.items():
        if typ == "Int64" and col in df.columns:
            df[col] = df[col].astype("Int64")
    return df

# Convenience loaders
def load_materials() -> pd.DataFrame:
    p = paths()["materials"]
    return read_csv_safe(p, SCHEMA_MATERIALS)

def load_processes() -> pd.DataFrame:
    p = paths()["processes"]
    return read_csv_safe(p, SCHEMA_PROCESSES)

def load_bom() -> pd.DataFrame:
    p = paths()["bom"]
    return read_csv_safe(p, SCHEMA_BOM)
