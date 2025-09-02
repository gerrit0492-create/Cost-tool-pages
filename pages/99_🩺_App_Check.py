# pages/99_🩺_App_Check.py

from __future__ import annotations
import ast, os, sys, json, re
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="🩺 App Check", page_icon="🩺", layout="wide")
st.title("🩺 Complete App Check")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------- config ----------
WIDGET_FUNCS = {
    "button", "checkbox", "radio", "selectbox", "multiselect",
    "slider", "text_input", "number_input", "file_uploader",
    "data_editor", "toggle", "date_input", "time_input", "color_picker"
}
DEBUG_PATTERNS = [
    "sys.path[0:3]", "root files", "utils files", "st.write(\"sys.path",
    "st.code(\"sys.path", "st.json(\"sys.path", "st.write('sys.path"
]
NETWORK_FUNCS = {("requests","get"), ("requests","post"), ("urllib.request","urlopen")}

# ---------- helpers ----------
class Analyzer(ast.NodeVisitor):
    def __init__(self, src: str):
        self.src = src
        self.streamlit_calls = []  # list[(lineno, fullname)]
        self.set_page_config_lines = []
        self.widget_labels = []    # list[(func, label, has_key, lineno)]
        self.top_level_network = []# list[(lineno, call)]
        self.in_func = 0
        super().__init__()

    def visit_FunctionDef(self, node):
        self.in_func += 1
        self.generic_visit(node)
        self.in_func -= 1
    visit_AsyncFunctionDef = visit_FunctionDef
    def visit_Lambda(self, node):
        self.in_func += 1
        self.generic_visit(node)
        self.in_func -= 1

    def visit_Call(self, node: ast.Call):
        # Full dotted name like st.button
        fullname = None
        if isinstance(node.func, ast.Attribute):
            # something.attr
            # extract base id (e.g. st / requests / urllib.request)
            parts = []
            cur = node.func
            while isinstance(cur, ast.Attribute):
                parts.insert(0, cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.insert(0, cur.id)
            elif isinstance(cur, ast.Attribute):  # nested
                # very rare case; best effort
                parts.insert(0, getattr(cur, "attr", "?"))
            fullname = ".".join(parts)

        # Record Streamlit calls
        if fullname and fullname.startswith("st."):
            self.streamlit_calls.append((node.lineno, fullname))
            if fullname == "st.set_page_config":
                self.set_page_config_lines.append(node.lineno)

            # widget labels + key presence
            fn = fullname.split(".", 1)[1]
            if fn in WIDGET_FUNCS:
                label = None
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    label = node.args[0].value
                has_key = any((isinstance(k.arg, str) and k.arg == "key") for k in node.keywords)
                self.widget_labels.append((fn, label, has_key, node.lineno))

        # Top-level network calls (outside functions) → fragile, flag it
        if fullname:
            for base, method in NETWORK_FUNCS:
                if fullname == f"{base}.{method}" and self.in_func == 0:
                    self.top_level_network.append((node.lineno, fullname))

        self.generic_visit(node)

def analyze_file(path: Path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(text, filename=str(path))
    a = Analyzer(text)
    a.visit(tree)

    # 1) set_page_config orde + multiplicity
    first_st_call = min([ln for ln, name in a.streamlit_calls], default=None)
    first_spc = min(a.set_page_config_lines, default=None)
    spc_ok_first = (first_spc is not None and (first_st_call is None or first_spc <= first_st_call))
    spc_count = len(a.set_page_config_lines)

    # 2) Dubbele widgetlabels zonder key
    seen = {}
    duplicates = []
    for fn, label, has_key, ln in a.widget_labels:
        if label is None:
            continue
        key = (fn, label)
        seen.setdefault(key, []).append((ln, has_key))
    for key, occ in seen.items():
        # duplicates if ≥2 occurrences AND minstens één zonder key
        if len(occ) >= 2 and any(not hk for _, hk in occ):
            duplicates.append({
                "widget": key[0], "label": key[1],
                "lines": [ln for ln, _ in occ],
                "hint": "Gebruik unieke key=... per widget met identiek label."
            })

    # 3) Debug-prints in code
    debug_hits = []
    for pat in DEBUG_PATTERNS:
        if pat in text:
            # alle regels waar pattern voorkomt
            lines = [i+1 for i,l in enumerate(text.splitlines()) if pat in l]
            debug_hits.append({"pattern": pat, "lines": lines})

    # 4) Top-level netwerkcalls
    net_hits = [{"line": ln, "call": call} for ln, call in a.top_level_network]

    return {
        "file": str(path.relative_to(ROOT)),
        "set_page_config_first": spc_ok_first,
        "set_page_config_count": spc_count,
        "first_streamlit_line": first_st_call,
        "first_set_page_config_line": first_spc,
        "duplicate_widget_labels": duplicates,
        "debug_hits": debug_hits,
        "top_level_network_calls": net_hits,
    }

def scan_repo(root: Path):
    py_files = []
    for p in [root] + [root / "pages", root / "utils"]:
        if p.exists():
            py_files += list(p.rglob("*.py"))
    # filter out __pycache__/venv etc.
    py_files = [p for p in py_files if ".venv" not in str(p) and "__pycache__" not in str(p)]
    results = [analyze_file(p) for p in sorted(py_files)]
    return results

results = scan_repo(ROOT)

# ---------- Presentatie ----------
bad = []
for r in results:
    flags = []
    if not r["set_page_config_first"]:
        flags.append("set_page_config niet eerst")
    if r["set_page_config_count"] > 1:
        flags.append("meerdere set_page_config calls")
    if r["duplicate_widget_labels"]:
        flags.append("dubbele widgetlabels zonder key")
    if r["debug_hits"]:
        flags.append("debug-prints in UI")
    if r["top_level_network_calls"]:
        flags.append("top-level netwerkcall")
    if flags:
        bad.append((r, flags))

st.subheader("Samenvatting")
ok_count = len(results) - len(bad)
st.write(f"✅ OK: **{ok_count}** bestanden  •  ⚠️ Issues in **{len(bad)}** bestanden  •  Totaal gescand: **{len(results)}**")

# Tabel met kernsignalen
import pandas as pd
rows = []
for r in results:
    rows.append({
        "file": r["file"],
        "SPC first": "✅" if r["set_page_config_first"] else "❌",
        "SPC count": r["set_page_config_count"],
        "dup labels?": "✅" if r["duplicate_widget_labels"] else "—",
        "debug hits?": "✅" if r["debug_hits"] else "—",
        "top-level net?": "✅" if r["top_level_network_calls"] else "—",
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True)

st.divider()
st.subheader("Details & fixes per bestand")

for r, flags in bad:
    st.markdown(f"### {r['file']}  {' • '.join('**'+f+'**' for f in flags)}")
    c1, c2, c3 = st.columns(3)
    c1.write(f"**eerste st.* op regel:** {r['first_streamlit_line']}")
    c2.write(f"**eerste set_page_config op regel:** {r['first_set_page_config_line']}")
    c3.write(f"**aantal set_page_config:** {r['set_page_config_count']}")

    if r["duplicate_widget_labels"]:
        st.warning("Dubbele widgetlabels zonder `key`:")
        st.json(r["duplicate_widget_labels"])
        st.caption("Fix: voeg `key=\"unieke_naam\"` toe aan elk widget met hetzelfde label binnen dezelfde pagina.")

    if r["debug_hits"]:
        st.info("Potentiële debug-prints die in de UI zichtbaar zijn:")
        st.json(r["debug_hits"])
        st.caption("Fix: verwijder of hang achter DEBUG-vlag; gebruik logging i.p.v. `st.write`.")

    if r["top_level_network_calls"]:
        st.error("Top-level netwerkcalls (lopen bij import en kunnen je UI blokkeren):")
        st.json(r["top_level_network_calls"])
        st.caption("Fix: verplaats requests naar functies en roep ze aan vanuit UI-events; geef altijd `timeout=` mee.")

st.divider()
st.subheader("Extra checks: utils/shared.py")

shared_path = ROOT / "utils" / "shared.py"
if shared_path.exists():
    txt = shared_path.read_text(encoding="utf-8", errors="ignore")
    hints = []
    # timeouts in requests.get
    for m in re.finditer(r"requests\.get\([^)]*\)", txt):
        call = m.group(0)
        if "timeout=" not in call:
            hints.append({"line": txt[:m.start()].count('\n')+1,
                          "issue": "requests.get zonder timeout", "call": call[:120]+"..."})
    # cache decorators
    cache_ok = ("@st.cache_data" in txt) or ("@st.cache_resource" in txt)
    st.write(f"• Cache-decorators gevonden: {'✅' if cache_ok else '⚠️ niet gevonden'}")
    if hints:
        st.warning("requests zonder `timeout=`:")
        st.json(hints)
else:
    st.warning("`utils/shared.py` niet gevonden.")

st.divider()
st.download_button(
    "⬇️ Download JSON-rapport",
    data=json.dumps(results, indent=2).encode("utf-8"),
    file_name="app_check_report.json",
    mime="application/json"
)

st.caption("Tip: Los issues op, refresh de pagina en check of de vlaggen verdwijnen. Deze check is statisch—runtime fouten zie je met jouw `guard(...)`.")
