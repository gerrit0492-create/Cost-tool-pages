from bootstrap import configure_page, init_state
configure_page(); init_state()

from utils.safe import run_safely
# pages/99_🩺_App_Check.py
# Robuuste App Check:
# - Scant .py-bestanden onder repo
# - Parseert met AST en vangt SyntaxError/UnicodeError af
# - Rapporteert per bestand: OK / FOUT + regel + melding
# - Extra checks: deprecated streamlit calls, requirements, grote bestanden
# - Crasht niet meer wanneer één file stuk is

import os
import ast
import io
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="🩺 App Check", page_icon="🩺", layout="wide")
st.title("🩺 App Check (robuuste parser + duidelijke fouten)")

ROOT = Path(".").resolve()

EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".streamlit", ".devcontainer", "data", "templates", "branding", "docs"
}
EXCLUDE_FILES = set()

def iter_py_files(base: Path):
    for p in base.rglob("*.py"):
        rel = p.relative_to(ROOT)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if p.name in EXCLUDE_FILES:
            continue
        yield p

def safe_read_text(path: Path) -> str:
    # Probeer UTF-8; zo niet, negeer onleesbare tekens (we willen de parser laten falen op echte syntax, niet op bytes)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")

def analyze_file(path: Path) -> dict:
    text = safe_read_text(path)
    info = {
        "path": str(path),
        "status": "OK",
        "error": "",
        "error_line": "",
        "deprecated": [],
        "imports": [],
        "streamlit_used": False,
        "size_kb": round(path.stat().st_size / 1024, 1),
        "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    }
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as e:
        info["status"] = "SYNTAX_ERROR"
        info["error"] = f"{e.__class__.__name__}: {e.msg}"
        info["error_line"] = f"line {e.lineno}, col {e.offset}"
        return info
    except Exception as e:
        info["status"] = "PARSE_ERROR"
        info["error"] = f"{e.__class__.__name__}: {e}"
        return info

    # Basisanalyse: imports en streamlit-gebruik
    imports = []
    deprecated = []
    streamlit_used = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            imports.append(mod)
            # detecteer deprecated streamlit api
            for n in node.names:
                name = n.name
                if name.startswith("experimental_"):
                    deprecated.append(f"from {mod} import {name}")
        elif isinstance(node, ast.Attribute):
            # st.experimental_rerun, st.experimental_show, etc.
            if isinstance(node.value, ast.Name) and node.value.id == "st":
                attr = node.attr
                if attr.startswith("experimental_"):
                    deprecated.append(f"st.{attr}")
                if attr == "experimental_rerun":
                    deprecated.append("st.experimental_rerun (gebruik st.rerun)")
                if attr == "cache":
                    deprecated.append("st.cache (overweeg st.cache_data/st.cache_resource)")
                if attr == "rerun":
                    pass
        elif isinstance(node, ast.Name):
            if node.id == "st":
                streamlit_used = True

    info["imports"] = sorted(set(imports))
    info["streamlit_used"] = streamlit_used
    info["deprecated"] = sorted(set(deprecated))
    return info

def scan_repo(base: Path):
    results = [analyze_file(p) for p in sorted(iter_py_files(base))]
    return results

with st.spinner("Repository scannen…"):
    results = scan_repo(ROOT)

df = pd.DataFrame(results)

# Overzicht
ok_n = (df["status"] == "OK").sum()
err_n = (df["status"] != "OK").sum()
st.metric("Bestanden OK", ok_n)
st.metric("Bestanden met fouten", err_n)

# Tabel met fouten eerst
df_sorted = df.sort_values(["status", "path"])
cols_show = ["status", "path", "error", "error_line", "size_kb", "modified"]
st.subheader("Resultaten")
st.dataframe(df_sorted[cols_show], use_container_width=True, height=420)

# Details per bestand (expanders)
st.subheader("Details per bestand")
for _, row in df_sorted.iterrows():
    with st.expander(f"{row['path']}  —  {row['status']}"):
        if row["error"]:
            st.error(f"{row['error']}  ({row['error_line']})")
        st.write(f"Streamlit gebruikt: {'ja' if row['streamlit_used'] else 'nee'}")
        if row["deprecated"]:
            st.warning("Gevonden deprecated API’s:\n- " + "\n- ".join(row["deprecated"]))
        if row["imports"]:
            st.caption("Imports: " + ", ".join(row["imports"]))

# Snelle checks
st.subheader("Snelle checks")
checks = []

# requirements.txt aanwezig?
req_path = ROOT / "requirements.txt"
checks.append(("requirements.txt", req_path.exists(), str(req_path)))
# data map
checks.append(("data/ bestaat", (ROOT/"data").exists(), "data/"))
# kernbestanden
for p in ["home.py", "pages/13_Marktdata.py", "pages/16_Routing_Kosten.py", "pages/18_Offerte_DOCX.py"]:
    checks.append((p, (ROOT/p).exists(), p))

df_checks = pd.DataFrame(checks, columns=["Check", "OK", "Pad"])
st.table(df_checks)

# Download ruwe resultaten
st.download_button(
    "⬇️ Download ruwe resultaten (CSV)",
    df_sorted.to_csv(index=False),
    file_name="app_check_results.csv",
    mime="text/csv"
)

st.caption("Tip: Klik op de expanders boven om te zien welk bestand precies stuk is (regel/kolom) en welke API’s gedeprecieerd zijn.")
