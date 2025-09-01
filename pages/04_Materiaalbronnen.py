# pages/04_Materiaalbronnen.py

import os, sys, traceback as _tb
import datetime as dt
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np  # eventueel gebruikt in utils

# ⬅️ Altijd als eerste Streamlit-call:
st.set_page_config(page_title="Materiaalbronnen & Scraping", page_icon="🧲", layout="wide")

# Repo-root op sys.path (robust)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Gedeelde logica importeren
try:
    from utils.shared import (
        MATERIALS, OTK_KEY, eurton,
        fetch_otk, fetch_lme_eur_ton
    )
except Exception:
    st.error("Kon utils.shared niet importeren.")
    st.code("".join(_tb.format_exc()))
    st.stop()

st.title("🧲 Materiaalbronnen & Scraping status")
st.caption("Live controles voor **Outokumpu** (RVS surcharges) en **LME Aluminium** (€/ton), incl. rekenhulp en cache-refresh.")

# -----------------------------
# Sectie: Outokumpu (RVS)
# -----------------------------
st.subheader("Outokumpu – RVS surcharges (€/ton)")

cols = st.columns([1, 1, 1, 2])
with cols[0]:
    if st.button("🔄 Refresh OTK cache (hard)"):
        try:
            # alleen clear aanroepen als beschikbaar (bij @st.cache_data)
            if hasattr(fetch_otk, "clear"):
                fetch_otk.clear()  # type: ignore[attr-defined]
                st.success("OTK-cache geleegd. Klik op 'Ophalen' om opnieuw te laden.")
            else:
                st.info("Geen cache op fetch_otk; niets te legen.")
        except Exception as e:
            st.warning(f"Kon cache niet legen: {e}")

with cols[1]:
    otk_go = st.button("📡 Ophalen")

if otk_go:
    st.session_state["_otk_last"] = dt.datetime.utcnow()

otk_time = st.session_state.get("_otk_last")

try:
    if otk_go or ("_otk_cached" not in st.session_state):
        otk = fetch_otk()
        st.session_state["_otk_cached"] = otk
    else:
        otk = st.session_state["_otk_cached"]
except Exception:
    otk = {}
    st.error("Fout bij ophalen Outokumpu.")
    st.code("".join(_tb.format_exc()))

if otk:
    df = pd.DataFrame(
        [{"OTK_key": k, "€/ton": v, "€/kg": eurton(v)} for k, v in otk.items()]
    ).sort_values("OTK_key")
    st.dataframe(df, use_container_width=True)
    tail = f"Laatste refresh: {otk_time.strftime('%Y-%m-%d %H:%M UTC')}" if otk_time else ""
    st.caption(f"Gevonden kwaliteiten: {', '.join(sorted(otk.keys()))}.  {tail}")
else:
    st.info("Nog geen waarden beschikbaar. Klik op **📡 Ophalen** om te proberen, of probeer later opnieuw.")

# Rekenhulp RVS (base + surcharge/1000)
st.markdown("#### RVS rekenhulp (€/kg)")
colm1, colm2, colm3 = st.columns([2, 1, 1])

# Alleen RVS-materialen tonen; veilige afhandeling als lijst leeg is
rvs_keys = [m for m, v in MATERIALS.items() if v.get("kind") == "stainless"]

with colm1:
    if rvs_keys:
        sel_rvs = st.selectbox("RVS kwaliteit", rvs_keys, index=0)
    else:
        st.warning("Geen RVS-materialen gevonden in MATERIALS.")
        sel_rvs = None

with colm2:
    base = MATERIALS.get(sel_rvs, {}).get("base_eurkg", 0.0) if sel_rvs else 0.0
    st.metric("Base €/kg", f"{base:.3f}")

with colm3:
    ref = OTK_KEY.get(sel_rvs, "") if sel_rvs else ""
    sur_ton = (otk or {}).get(ref)
    sur_kg = eurton(sur_ton) if sur_ton else 0.0
    st.metric("Surcharge €/kg", f"{sur_kg:.3f}")

st.success(f"**Indicatieve materiaalprijs {sel_rvs or '—'}: € {(base + (sur_kg or 0.0)):.3f}/kg**")

st.divider()

# -----------------------------
# Sectie: LME Aluminium
# -----------------------------
st.subheader("LME Aluminium (€/ton)")

c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("🔄 Refresh LME cache (hard)"):
        try:
            if hasattr(fetch_lme_eur_ton, "clear"):
                fetch_lme_eur_ton.clear()  # type: ignore[attr-defined]
                st.success("LME-cache geleegd. Klik op 'Ophalen'.")
            else:
                st.info("Geen cache op fetch_lme_eur_ton; niets te legen.")
        except Exception as e:
            st.warning(f"Kon cache niet legen: {e}")
with c2:
    lme_go = st.button("📡 Ophalen")

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
    st.code("".join(_tb.format_exc()))

colx, coly, colz = st.columns([1, 1, 2])
with colx:
    st.metric("LME €/ton", f"{lme_val:.0f}" if lme_val else "—")
with coly:
    st.caption(lme_src)
with colz:
    st.caption(f"{'Laatste refresh: ' + lme_time.strftime('%Y-%m-%d %H:%M UTC') if lme_time else ''}")

st.markdown("#### Alu prijs (€/kg) met premie & conversie")
p1, p2, p3, p4 = st.columns(4)
with p1:
    lme_ton_manual = st.number_input("LME (€/ton, override)", 0.0, 100000.0, float(lme_val or 2200.0), 10.0)
with p2:
    prem = st.number_input("Regiopremie (€/kg)", 0.0, 10.0, 0.25, 0.01)
with p3:
    conv_add = st.number_input("Conversie-opslag (€/kg)", 0.0, 10.0, 0.40, 0.01)
with p4:
    calc = eurton(lme_ton_manual) + prem + conv_add
    st.metric("Indicatieve €/kg", f"{calc:.3f}")

st.divider()

# -----------------------------
# Diagnose & tips
# -----------------------------
with st.expander("🔍 Diagnose & tips"):
    st.write("""
- **Bronnen**  
  - Outokumpu: publiek surcharges-overzicht (HTML). Parser zoekt naar bekende grade-labels (304/316L/2205/2507/904L) en bedragen met `€` of `€/t`.  
  - LME: TradingEconomics commodity-pagina; parser pakt `data-price` en rekent USD→EUR met een vaste FX-aanname (in `shared.py`).
- **Actualiteit**  
  - OTK-cache: ~3 uur. LME-cache: ~30 min. Via de **Refresh**-knoppen maak je de cache leeg.
- **Validatie**  
  - Vergelijk waarden handmatig met leveranciersquotes. “Surcharge €/kg” = `€/ton / 1000`.
- **Fallback**  
  - Als scraping faalt, gebruik de **manual** invoervelden in **Calculatie** (OTK of LME override).
""")
