import os, sys, json, traceback, time
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Diagnose", page_icon="🧪", layout="wide")
st.title("🧪 Diagnose - runtime & integriteit")

def check(name, fn):
    ok, err, extra = True, "", None
    t0 = time.time()
    try:
        extra = fn()
    except Exception as e:
        ok = False
        err = "".join(traceback.format_exception_only(type(e), e)).strip()
    dt = (time.time() - t0) * 1000
    st.write(f"**{name}** - {'✅ OK' if ok else '❌ FOUT'}  (_{dt:.0f} ms_)")
    if extra not in (None, ""):
        with st.expander("Details", expanded=not ok):
            st.write(extra if isinstance(extra, str) else extra)
    if not ok:
        st.error(err)
    return ok

# 1) Python & versies
def env_info():
    import platform
    info = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "file": __file__,
    }
    try:
        import streamlit, pandas, numpy, plotly, matplotlib, altair, openpyxl, xlsxwriter, reportlab
        info["packages"] = {
            "streamlit": streamlit.__version__,
            "pandas": pandas.__version__,
            "numpy": numpy.__version__,
            "plotly": plotly.__version__,
            "matplotlib": matplotlib.__version__,
            "altair": altair.__version__,
            "openpyxl": openpyxl.__version__,
            "xlsxwriter": xlsxwriter.__version__,
            "reportlab": reportlab.__version__,
        }
    except Exception as e:
        info["packages_error"] = str(e)
    return info

# 2) Bestandsstructuur
def list_repo():
    root = Path(__file__).resolve().parent.parent  # repo-root (1 niveau boven /pages)
    items = {
        "root": str(root),
        "root_files": sorted([p.name for p in root.glob("*") if p.is_file()])[:50],
        "pages": sorted([p.name for p in (root / "pages").glob("*.py")]) if (root / "pages").exists() else "geen pages/",
    }
    return items

# 3) Secrets (zonder ze te tonen)
def secrets_status():
    keys = []
    try:
        keys = list(st.secrets.keys())
    except Exception as e:
        return {"error": str(e)}
    return {"available_keys": keys}

# 4) Imports die vaak misgaan (relatieve paden)
def try_local_imports():
    # Voeg repo-root aan sys.path toe zodat from <module> import ... werkt
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.append(str(root))
    results = {}
    candidates = [
        "home",           # je home.py
        "utils",          # vaak gebruikte hulpfuncties
        "config",         # eigen config
    ]
    for mod in candidates:
        try:
            m = __import__(mod)
            results[mod] = "OK"
        except Exception as e:
            results[mod] = f"ImportError: {e}"
    return results

# 5) Schrijf/lees test (rechten + paden)
def io_test():
    tmp = Path.cwd() / "tmp_diagnose_write.txt"
    tmp.write_text("diagnose ok", encoding="utf-8")
    content = tmp.read_text(encoding="utf-8")
    tmp.unlink(missing_ok=True)
    return {"write_read": content}

# 6) Session state sanity
def session_state_info():
    st.session_state.setdefault("diagnose_counter", 0)
    st.session_state["diagnose_counter"] += 1
    return dict(st.session_state)

# 7) Cache sanity (resetknop)
if st.button("Cache legen (cache_data & cache_resource)"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.success("Cache(s) geleegd. Herlaad de pagina.")

# Uitvoeren
check("Omgevingsinfo & pakketversies", env_info)
check("Repo & pages-structuur", list_repo)
check("Secrets beschikbaar?", secrets_status)
check("Importtest (home/utils/config)", try_local_imports)
check("I/O-test (schrijven/lezen)", io_test)
check("Session state", session_state_info)

# 8) Laat laatste exception uit andere pagina's zien als die in session is gezet
if "last_exception" in st.session_state:
    st.warning("Er is eerder een exception opgetreden in een andere pagina:")
    st.exception(st.session_state["last_exception"])
