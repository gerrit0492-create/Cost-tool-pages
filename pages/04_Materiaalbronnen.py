# pages/04_Materiaalbronnen.py

from __future__ import annotations
import sys
from pathlib import Path
import datetime as dt
import traceback as _tb

import streamlit as st
import pandas as pd

# 1) Altijd eerst page config
st.set_page_config(page_title="Materiaalbronnen & Scraping", page_icon="🧲", layout="wide")

# 2) Repo-root op sys.path (werkt in Streamlit Cloud en lokaal)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 3) Imports uit jouw shared utils
try:
    from utils.shared import (
        MATERIALS, OTK_KEY, eurton,
        fetch_otk, fetch_lme_eur_ton
    )
except Exception:
    st.error("Kon utils.shared niet importeren.")
    st.code("".join(_tb.format_exc()))
    st.stop()

# 4) Debug-schakelaar (standaard UIT). Activeer via ?debug=1 of secrets.DEBUG=true
DEBUG = (st.query_params.get("debug", ["0"])[0] in ("1", "true", "True")) or bool(st.secrets.get("DEBUG", False))

def _debug_panel():
    st.subheader("🔧 Debug")
    st.code(f"ROOT = {ROOT}")
    st.code(f"sys.path[0:3] = {sys.path[0:3]!r}")

if DEBUG:
    _debug_panel()

st.title("🧲 Materiaalbronnen & Scraping status")
st.caption("Live controles voor **Outokumpu** (RVS surcharges) en **LME Aluminium** (€/ton), incl. rekenhulp en cache-refresh.")

# 5) Helpers voor cache/refresh-gedrag
def clear_cache_for(func) -> bool:
    """
    Probeer cache van een (mogelijk) @st.cache_data functie te legen.
    Werkt alleen als func een .clear attribuut heeft.
    """
    try:
        if hasattr(func, "clear"):
            func.clear()  # type: ignore[attr-defined]
            return True
    except Exception:
        pass
    return False

# =========================
# A) Outokumpu (RVS)
# =========================
st.subheader("Outokumpu – RVS surcharges (€/ton)")

otk_cols = st.columns([1, 1, 1, 2])
with otk_cols[0]:
    if st.button("🔄 Refresh OTK cache (hard)", key="otk_refresh"):
        if clear_cache_for(fetch_otk):
            st.success("OTK-cache geleegd. Klik op ‘Ophalen’ om opnieuw te laden.")
        else:
            st.info("Geen cache op fetch_otk gevonden (of al leeg).")

with otk_cols[1]:
    otk_go = st.button("📡 Ophalen", key="otk_fetch")

if otk_go:
    st.session_state["_otk_last"] = dt.datetime.utcnow()

otk_time = st.session_state.get("_otk_last")

# Ophalen + cachen in session (simpele UI-cache los van @st.cache_data)
try:
    if otk_go or ("_otk_cached" not in st.session_state):
        otk = fetch_otk() or {}
        st.session_state["_otk_cached"] = otk
    else:
        otk = st.session_state["_otk_cached"]
except Exception:
    otk = {}
    st.error("Fout bij ophalen Outokumpu-surcharges.")
    if DEBUG:
        st.code("".join(_tb.format_exc()))

if otk:
    df_otk = pd.DataFrame(
        [{"OTK_key": k, "€/ton": v, "€/kg": eurton(v)} for k, v in otk.items()]
    ).sort_values("OTK_key")
    st.dataframe(df_otk, use_container_width=True)
    tail = f"Laatste refresh: {otk_time.strftime('%Y-%m-%d %H:%M UTC')}" if otk_time else ""
    st.caption(f"Gevonden kwaliteiten: {', '.join(sorted(otk.keys()))}.  {tail}")
else:
    st.info("Nog geen waarden beschikbaar. Klik op **📡 Ophalen** of probeer later opnieuw.")

# Rekenhulp RVS
st.markdown("#### RVS rekenhulp (€/kg)")
rv_cols = st.columns([2, 1, 1])

rvs_keys = [m for m, v in MATERIALS.items() if v.get("kind") == "stainless"]

with rv_cols[0]:
    if rvs_keys:
        sel_rvs = st.selectbox("RVS kwaliteit", rvs_keys, index=0, key="sel_rvs_grade")
    else:
        st.warning("Geen RVS-materialen gevonden in MATERIALS.")
        sel_rvs = None

with rv_cols[1]:
    base = MATERIALS.get(sel_rvs, {}).get("base_eurkg", 0.0) if sel_rvs else 0.0
    st.metric("Base €/kg", f"{base:.3f}")

with rv_cols[2]:
    ref = OTK_KEY.get(sel_rvs, "") if sel_rvs else ""
    sur_ton = (otk or {}).get(ref)
    sur_kg = eurton(sur_ton) if sur_ton else 0.0
    st.metric("Surcharge €/kg", f"{sur_kg:.3f}")

st.success(f"**Indicatieve materiaalprijs {sel_rvs or '—'}: € {(base + (sur_kg or 0.0)):.3f}/kg**")

st.divider()

# =========================
# B) LME Aluminium
# =========================
st.subheader("LME Aluminium (€/ton)")

lme_cols = st.columns(4)
with lme_cols[0]:
    if st.button("🔄 Refresh LME cache (hard)", key="lme_refresh"):
        if clear_cache_for(fetch_lme_eur_ton):
            st.success("LME-cache geleegd. Klik op ‘Ophalen’.")
        else:
            st.info("Geen cache op fetch_lme_eur_ton gevonden (of al leeg).")
with lme_cols[1]:
    lme_go = st.button("📡 Ophalen", key="lme_fetch")

if lme_go:
    st.session_state["_lme_last"] = dt.datetime.utcnow()

lme_time = st.session_state.get("_lme_last")
lme_val, lme_src = (None, "n/a")

try:
    if lme_go or ("_lme_cached" not in st.session_state):
        lme_val, lme_src = fetch_lme_eur_ton()
        st.session_state["_lme_cached"] = (lme_val, lme_src)
    else:
        lme_val, lme_src = st.session_state["_lme_cached"]
except Exception:
    st.error("Fout bij ophalen LME.")
    if DEBUG:
        st.code("".join(_tb.format_exc()))

met_cols = st.columns([1, 1, 2])
with met_cols[0]:
    st.metric("LME €/ton", f"{lme_val:.0f}" if lme_val else "—")
with met_cols[1]:
    st.caption(lme_src or "—")
with met_cols[2]:
    st.caption(f"{'Laatste refresh: ' + lme_time.strftime('%Y-%m-%d %H:%M UTC') if lme_time else ''}")

st.markdown("#### Alu prijs (€/kg) met premie & conversie")
p1, p2, p3, p4 = st.columns(4)
with p1:
    lme_ton_manual = st.number_input(
        "LME (€/ton, override)", 0.0, 100000.0, float(lme_val or 2200.0), 10.0, key="lme_override"
    )
with p2:
    prem = st.number_input("Regiopremie (€/kg)", 0.0, 10.0, 0.25, 0.01, key="alu_prem")
with p3:
    conv_add = st.number_input("Conversie-opslag (€/kg)", 0.0, 10.0, 0.40, 0.01, key="alu_conv")
with p4:
    calc = eurton(lme_ton_manual) + prem + conv_add
    st.metric("Indicatieve €/kg", f"{calc:.3f}")

st.divider()

# =========================
# C) Diagnose & tips
# =========================
with st.expander("🔍 Diagnose & tips"):
    st.write("""
- **Bronnen**  
  - Outokumpu: publiek surcharges-overzicht (HTML). Parser zoekt naar bekende grade-labels (304/316L/2205/2507/904L) en bedragen met `€` of `€/t`.  
  - LME: commodity-pagina; parser pakt de koers en rekent zo nodig naar EUR/ton in `shared.py`.
- **Actualiteit**  
  - OTK-cache: typisch een paar uur. LME-cache: ±30 min. Via de **Refresh**-knoppen maak je de cache leeg.
- **Validatie**  
  - Vergelijk waarden handmatig met leveranciersquotes. “Surcharge €/kg” = `€/ton / 1000`.
- **Fallback**  
  - Als scraping faalt, gebruik de manual invoervelden in **Calculatie** (OTK of LME override).
""")
