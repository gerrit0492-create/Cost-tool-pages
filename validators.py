# utils/validators.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd

@dataclass
class Schema:
    name: str
    columns: List[str]
    dtypes: Dict[str, str] | None = None
    defaults: Dict[str, Any] | None = None

@dataclass
class Diff:
    missing: List[str]
    unexpected: List[str]
    dtype_mismatch: List[Tuple[str, str, str]]  # (col, got, expected)

@dataclass
class FixReport:
    reordered: bool
    filled_defaults: List[str]
    casted_types: List[Tuple[str, str, str]]
    dropped_unexpected: List[str]

ROUTING_SCHEMA = Schema(
    name="routing_df",
    columns=[
        "Step","Proces","Qty_per_parent","Cycle_min","Setup_min","Attend_pct",
        "kWh_pc","QA_min_pc","Scrap_pct","Parallel_machines","Batch_size","Queue_days"
    ],
    dtypes={
        "Step":"int64","Proces":"object","Qty_per_parent":"float64","Cycle_min":"float64","Setup_min":"float64",
        "Attend_pct":"float64","kWh_pc":"float64","QA_min_pc":"float64","Scrap_pct":"float64",
        "Parallel_machines":"int64","Batch_size":"int64","Queue_days":"float64"
    },
    defaults={
        "Step":10,"Proces":"CNC","Qty_per_parent":1.0,"Cycle_min":1.0,"Setup_min":0.0,
        "Attend_pct":100.0,"kWh_pc":0.0,"QA_min_pc":0.0,"Scrap_pct":0.0,
        "Parallel_machines":1,"Batch_size":1,"Queue_days":0.0
    }
)

BOM_SCHEMA = Schema(
    name="bom_df",
    columns=["Part","Qty","UnitPrice","Scrap_pct"],
    dtypes={"Part":"object","Qty":"float64","UnitPrice":"float64","Scrap_pct":"float64"},
    defaults={"Part":"Item","Qty":1.0,"UnitPrice":0.0,"Scrap_pct":0.0}
)

def diff_schema(df: pd.DataFrame, schema: Schema) -> Diff:
    cols = list(df.columns)
    missing = [c for c in schema.columns if c not in cols]
    unexpected = [c for c in cols if c not in schema.columns]
    dtype_mismatch: List[Tuple[str,str,str]] = []
    if schema.dtypes:
        for c, exp in schema.dtypes.items():
            if c in df.columns:
                got = str(df[c].dtype)
                # pandas kan int64/float64 soms als object lezen na data_editor; toleranter casten
                if got != exp:
                    dtype_mismatch.append((c, got, exp))
    return Diff(missing, unexpected, dtype_mismatch)

def _safe_cast(series: pd.Series, target_dtype: str) -> pd.Series:
    try:
        if target_dtype.startswith("int"):
            # eerst naar float → afronden → naar Int64 (nullable), daarna naar int64 indien geen NA
            s = pd.to_numeric(series, errors="coerce")
            if s.isna().any():
                return s.astype("Int64")
            return s.astype("int64")
        if target_dtype.startswith("float"):
            return pd.to_numeric(series, errors="coerce").astype("float64")
        if target_dtype in ("object","string"):
            return series.astype("string")
        return series.astype(target_dtype)
    except Exception:
        # fallback: laat kolom staan zoals is
        return series

def fix_schema(df: pd.DataFrame, schema: Schema, drop_unexpected: bool = False) -> Tuple[pd.DataFrame, FixReport]:
    df2 = df.copy()

    # Voeg missende kolommen toe met defaults of NaN
    filled: List[str] = []
    for c in schema.columns:
        if c not in df2.columns:
            default = (schema.defaults or {}).get(c)
            df2[c] = default
            filled.append(c)

    # Optioneel: onverwachte kolommen droppen
    unexpected_now = [c for c in df2.columns if c not in schema.columns]
    dropped: List[str] = []
    if drop_unexpected and unexpected_now:
        df2 = df2.drop(columns=unexpected_now)
        dropped = unexpected_now

    # Typecasts
    casted: List[Tuple[str,str,str]] = []
    if schema.dtypes:
        for c, exp in schema.dtypes.items():
            if c in df2.columns:
                got = str(df2[c].dtype)
                if got != exp:
                    before = got
                    df2[c] = _safe_cast(df2[c], exp)
                    after = str(df2[c].dtype)
                    casted.append((c, before, after))

    # Reorder
    reordered = False
    if list(df2.columns) != schema.columns:
        df2 = df2[[c for c in schema.columns if c in df2.columns]]
        reordered = True

    return df2, FixReport(reordered, filled, casted, dropped)
