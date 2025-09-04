from __future__ import annotations
import pathlib as pl, re, sys, traceback

ROOT = pl.Path(".")
PAGES = ROOT / "pages"
UTILS = ROOT / "utils"
UTILS.mkdir(exist_ok=True)

def info(msg: str):
    print(f"[auto-fix] {msg}", flush=True)

def write_file(path: pl.Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    info(f"Wrote {path}")

def safe_run(fn, *a, **k):
    try:
        return fn(*a, **k)
    except Exception as e:
        print("[auto-fix] ERROR:", type(e).__name__, e, file=sys.stderr)
        traceback.print_exc()
        return None

# 1) Nieuwe utils/shared.py
write_file(
    UTILS / "shared.py",
    """
from __future__ import annotations

try:
    from .io import SCHEMA_MATERIALS, SCHEMA_PROCESSES, SCHEMA_BOM, read_csv_safe, paths
except Exception:
    SCHEMA_MATERIALS, SCHEMA_PROCESSES, SCHEMA_BOM = {}, {}, {}
    def read_csv_safe(*a, **k): return None
    def paths():
        from pathlib import Path
        d = Path("data")
        return {
            "root": Path("."), "data": d,
            "materials": d/"materials_db.csv",
            "processes": d/"processes_db.csv",
            "bom": d/"bom_template.csv"
        }

MATERIALS = SCHEMA_MATERIALS
PROCESSES = SCHEMA_PROCESSES
BOM = SCHEMA_BOM

__all__ = [
    "SCHEMA_MATERIALS","SCHEMA_PROCESSES","SCHEMA_BOM",
    "read_csv_safe","paths","MATERIALS","PROCESSES","BOM"
]
""".strip()+"\n"
)

# 2) Nieuwe utils/safe.py
write_file(
    UTILS / "safe.py",
    """
from __future__ import annotations
import streamlit as st
from typing import Callable, Any

def run_safely(label: str, fn: Callable[..., Any], *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        st.error(f"{label} faalde: {type(e).__name__}: {e}")
        return None

def guard(fn: Callable[[], Any]) -> None:
    try:
        fn()
    except Exception as e:
        st.error(f"Deze page kon niet starten: {type(e).__name__}: {e}")
        st.stop()
""".strip()+"\n"
)

# 3) Page fixes
IMPORT_OLD = re.compile(r"from\s+utils\.shared\s+import\s+([^\n]+)")
RENAME_MAP = {"MATERIALS": "SCHEMA_MATERIALS", "PROCESSES": "SCHEMA_PROCESSES", "BOM": "SCHEMA_BOM"}
HAS_GUARD = re.compile(r"\bguard\s*\(\s*main\s*\)\s*$", re.M)
UNICODE_FIXES = {"Δ": "delta_", "–": "-", "—": "-", "’": "'", "“": '"', "”": '"', "•": "-"}

def normalize_unicode(s: str) -> str:
    for b, g in UNICODE_FIXES.items():
        s = s.replace(b, g)
    return s

def fix_imports(src: str) -> str:
    if "from utils.io import" in src:
        return src
    m = IMPORT_OLD.search(src)
    if not m:
        return src
    items = [i.strip() for i in m.group(1).split(",")]
    mapped, passthrough = [], []
    for it in items:
        n = it.split(" as ")[0].strip()
        if n in RENAME_MAP:
            mapped.append(f"{RENAME_MAP[n]} as {n}")
        elif n in ("read_csv_safe", "paths"):
            passthrough.append(n)
    imp = []
    if mapped: imp.extend(mapped)
    if passthrough: imp.extend(passthrough)
    if imp:
       
