# bovenin elk .py bestand
from bootstrap import configure_page, init_state
configure_page(); init_state()
import streamlit as st, traceback

def guard(run):
    try:
        run()
    except Exception:
        err = traceback.format_exc()
        # toon in UI
        st.exception(err)
        # bewaar ook in session_state zodat Diagnose-pagina hem kan tonen
        st.session_state["last_exception"] = err
# pages/09_Dashboard.py
import os, sys, pandas as pd, numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

import streamlit as st
from utils.shared import build_powerbi_facts, MACHINE_RATES, LABOR

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Dashboard")

# Brondata uit sessie opbouwen tot Fact-tabellen (als export nog niet gebruikt is)
routing = st.session_state.get("routing_df")
bom     = st.session_state.get("bom_df")
if routing is None or bom is None:
    st.warning("Geen data in sessie. Ga naar **01_Calculatie**.")
    st.stop()

project = st.session_state.get("project","Demo")
Q       = st.session_state.get("Q",50)
netkg   = st.session_state.get("netkg",2.0)
price   = st.session_state.get("price",3.5)
energy  = st.session_state.get("energy",0.20)
price_src = st.session_state.get("price_src","manual")
res = st.session_state.get("res", {"mat_pc":0,"conv_total":0,"lean_total":0,"buy_total":0,"total_pc":0})
mc = st.session_state.get("mc_samples")

facts = build_powerbi_facts(
    routing_df=pd.DataFrame(routing), bom_df=pd.DataFrame(bom),
    Q=Q, netkg=netkg, mat_price_eurkg=price, energy_eur_kwh=energy,
    labor_rate=LABOR, machine_rates=MACHINE_RATES,
    project=project, materiaal=st.session_state.get("mat",""), price_source=price_src,
    mc_samples=mc, res=res
)

fr, frt, fb = facts["FactRun"], facts["FactRouting"], facts["FactBOM"]

# Filters
c1,c2 = st.columns(2)
with c1:
    sel_project = st.selectbox("Project", sorted(fr["Project"].astype(str).unique()))
with c2:
    dates = pd.to_datetime(fr["RunDate"]).dt.date.unique()
    sel_date = st.selectbox("RunDate", sorted(dates))

mask = (fr["Project"]==sel_project) & (pd.to_datetime(fr["RunDate"]).dt.date==sel_date)
fr_v = fr[mask]
frt_v= frt[(frt["Project"]==sel_project) & (pd.to_datetime(frt["RunDate"]).dt.date==sel_date)]
fb_v = fb[(fb["Project"]==sel_project) & (pd.to_datetime(fb["RunDate"]).dt.date==sel_date)]

kc1,kc2,kc3,kc4,kc5 = st.columns(5)
kc1.metric("Materiaal €/stuk", f"€ {fr_v['Mat_pc'].mean():.2f}" if not fr_v.empty else "—")
kc2.metric("Conversie",        f"€ {fr_v['Conv_total'].sum():.2f}" if not fr_v.empty else "—")
kc3.metric("Lean",             f"€ {fr_v['Lean_total'].sum():.2f}" if not fr_v.empty else "—")
kc4.metric("Inkoop",           f"€ {fr_v['Buy_total'].sum():.2f}" if not fr_v.empty else "—")
kc5.metric("Kostprijs/stuk",   f"€ {fr_v['UnitCost'].mean():.2f}" if not fr_v.empty else "—")

st.markdown("### Routing kosten per proces")
if not frt_v.empty:
    piv = frt_v.groupby("Process")[["Cost_Machine","Cost_Labor","Cost_Energy","Cost_Lean"]].sum().reset_index()
    st.bar_chart(piv.set_index("Process"))

st.markdown("### Top BOM kosten")
if not fb_v.empty:
    top = fb_v.sort_values("Cost_Run", ascending=False).head(10)
    st.dataframe(top[["Part","Qty_Run","Cost_Run"]], use_container_width=True)
