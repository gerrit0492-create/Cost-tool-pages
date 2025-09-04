# pages/00_Repo_Diagnostics.py
import os, sys, textwrap, streamlit as st

st.set_page_config(page_title="Diagnose", page_icon="🩺", layout="wide")
st.title("🩺 Repo & App Diagnose")

ROOT = os.getcwd()

def tree(root, max_depth=3):
    out = []
    for base, dirs, files in os.walk(root):
        depth = base.replace(root, "").count(os.sep)
        if depth > max_depth:
            continue
        indent = "  " * depth
        out.append(f"{indent}{os.path.basename(base) or '/'}")
        for f in sorted(files):
            out.append(f"{indent}  └─ {f}")
    return "\n".join(out)

st.subheader("📁 Bestandsstructuur (max 3 niveaus)")
st.code(tree(ROOT, 3), language="text")

st.subheader("✅ Vereiste paden aanwezig?")
checks = {
    "home.py": os.path.exists(os.path.join(ROOT, "home.py")),
    "pages/": os.path.exists(os.path.join(ROOT, "pages")),
    "utils/perplexity_ingest.py": os.path.exists(os.path.join(ROOT, "utils", "perplexity_ingest.py")),
    "data/": os.path.exists(os.path.join(ROOT, "data")),
    "data/material_prices.csv": os.path.exists(os.path.join(ROOT, "data", "material_prices.csv")),
    "data/labor_rates.csv": os.path.exists(os.path.join(ROOT, "data", "labor_rates.csv")),
    "data/bom_current.json": os.path.exists(os.path.join(ROOT, "data", "bom_current.json")),
}

ok, bad = [], []
for k, v in checks.items():
    (ok if v else bad).append(k)
col1, col2 = st.columns(2)
with col1: st.success("Aanwezig:\n- " + "\n- ".join(ok) if ok else "-")
with col2: st.error("Ontbreekt:\n- " + "\n- ".join(bad) if bad else "-")

st.subheader("ℹ️ Versies")
st.write({
    "python": sys.version.split()[0],
    "streamlit": getattr(sys.modules.get("streamlit"), "__version__", "unknown")
})

st.caption("Tip: zie je st.experimental_rerun()? Vervang door st.rerun() in je pagina's.")
