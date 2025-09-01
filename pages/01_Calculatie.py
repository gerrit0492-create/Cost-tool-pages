# --- robust path & import diagnostics (plak bovenaan) ---
import os, sys, traceback
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Log de zichtbare paden/bestanden naar de Streamlit logs
try:
    import streamlit as st
    st.write("sys.path[0:3] →", sys.path[:3])
    st.write("root files →", os.listdir(ROOT))
    if os.path.isdir(os.path.join(ROOT, "utils")):
        st.write("utils files →", os.listdir(os.path.join(ROOT, "utils")))
except Exception:
    pass

# Probeer import en toon volledige traceback als het misgaat
try:
    from utils.shared import *
except Exception:
    import streamlit as st
    st.error("Kon `utils.shared` niet importeren. Zie traceback hieronder:")
    st.code("".join(traceback.format_exc()))
    st.stop()
# pages/01_Calculatie.py
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

import io, streamlit as st, pandas as pd, plotly.express as px, plotly.graph_objects as go
from utils.shared import *

st.set_page_config(page_title="Calculatie", page_icon="🧮", layout="wide")
st.title("Calculatie")

# Invoer
c0,c1,c2,c3 = st.columns(4)
with c0: project = st.text_input("Project", st.session_state.get("project","Demo"))
with c1: Q = st.number_input("Aantal stuks (Q)", 1, 100000, st.session_state.get("Q",50))
with c2: mat = st.selectbox("Materiaal", list(MATERIALS.keys()), index=list(MATERIALS.keys()).index(st.session_state.get("mat","1.4462_Duplex")) if st.session_state.get("mat") in MATERIALS else 0)
with c3: netkg = st.number_input("Netto kg/stuk", 0.01, 10000.0, st.session_state.get("netkg",2.0))

# Materiaalprijs
kind = MATERIALS[mat]["kind"]; src="fixed"; price=MATERIALS[mat]["base_eurkg"]
with st.expander("Materiaalprijs", expanded=True):
    if kind=="stainless":
        mode=st.radio("Outokumpu bron",["Auto","Manual"],horizontal=True)
        manual_otk=st.number_input("OTK (€/ton)",0.0,100000.0,0.0,10.0)
        if mode=="Auto":
            data=fetch_otk(); sur=eurton(data.get(OTK_KEY.get(mat,""),0.0)); src="OTK scraped"
        else:
            sur=eurton(manual_otk); src="OTK manual"
        price=MATERIALS[mat]["base_eurkg"]+sur
    elif kind=="aluminium":
        lme_mode=st.radio("LME bron",["Auto","Manual"],horizontal=True)
        manual_lme=st.number_input("LME (€/ton)",0.0,100000.0,2200.0,10.0)
        prem=st.number_input("Regiopremie (€/kg)",0.0,10.0,0.25,0.01)
        conv_add=st.number_input("Conversie-opslag (€/kg)",0.0,10.0,0.40,0.01)
        if lme_mode=="Auto":
            lme,s=fetch_lme_eur_ton(); 
            if lme is None: lme,s=manual_lme,"LME manual"
        else:
            lme,s=manual_lme,"LME manual"
        price=eurton(lme)+prem+conv_add; src=f"{s} + prem+conv"
st.success(f"Actuele prijs: € {price:.3f}/kg  •  {src}")

# Lean/energie
with st.expander("Lean / Energie / Transport"):
    energy=st.number_input("Energie (€/kWh)",0.0,2.0,st.session_state.get("energy",0.20),0.01)
    storage_days=st.number_input("Opslagdagen",0.0,365.0,st.session_state.get("storage_days",0.0),0.5)
    storage_cost=st.number_input("Opslagkosten (€/dag/batch)",0.0,2000.0,st.session_state.get("storage_cost",0.0),0.5)
    km=st.number_input("Transport (km)",0.0,100000.0,st.session_state.get("km",0.0),1.0)
    eur_km=st.number_input("Tarief (€/km)",0.0,50.0,st.session_state.get("eur_km",0.0),0.1)
    rework=st.number_input("Herbewerkingskans (%)",0.0,100.0,st.session_state.get("rework",0.0),0.5)/100.0
    rework_min=st.number_input("Herbewerkingsminuten/stuk",0.0,240.0,st.session_state.get("rework_min",0.0),1.0)

# Routing/BOM
if "routing_df" not in st.session_state:
    st.session_state["routing_df"]=pd.DataFrame([{"Step":10,"Proces":"CNC","Qty_per_parent":1.0,"Cycle_min":6.0,"Setup_min":20.0,"Attend_pct":100,"kWh_pc":0.18,"QA_min_pc":0.5,"Scrap_pct":0.02,"Parallel_machines":1,"Batch_size":50,"Queue_days":0.5}],columns=ROUTING_COLS)
if "bom_df" not in st.session_state:
    st.session_state["bom_df"]=pd.DataFrame([{"Part":"Voorbeeld","Qty":1,"UnitPrice":1.50,"Scrap_pct":0.01}],columns=BOM_COLS)

st.subheader("Routing")
st.session_state["routing_df"]=pd.DataFrame(st.data_editor(st.session_state["routing_df"], num_rows="dynamic", use_container_width=True))
st.subheader("BOM / Inkoop")
st.session_state["bom_df"]=pd.DataFrame(st.data_editor(st.session_state["bom_df"], num_rows="dynamic", use_container_width=True))

# Bereken
res=cost_once(st.session_state["routing_df"], st.session_state["bom_df"], Q, netkg, price,
              energy, LABOR, MACHINE_RATES, storage_days, storage_cost, km, eur_km, rework, rework_min)
c1,c2,c3,c4,c5=st.columns(5)
c1.metric("Materiaal €/stuk", f"€ {res['mat_pc']:.2f}")
c2.metric("Conversie", f"€ {res['conv_total']:.2f}")
c3.metric("Lean", f"€ {res['lean_total']:.2f}")
c4.metric("Inkoop", f"€ {res['buy_total']:.2f}")
c5.metric("Kostprijs/stuk", f"€ {res['total_pc']:.2f}")

# Breakdown plot
st.plotly_chart(go.Figure(go.Pie(labels=["Materiaal","Conversie","Lean","Inkoop"],
                                 values=[res['mat_pc'],res['conv_total'],res['lean_total'],res['buy_total']])),
                use_container_width=True)

# Monte-Carlo
with st.expander("Monte-Carlo"):
    mc_on=st.checkbox("Aanzetten",False)
    iters=st.number_input("Iteraties",100,20000,1000,100)
    sd_mat=st.number_input("σ materiaal (%)",0.0,0.5,0.05,0.01)
    sd_cycle=st.number_input("σ cyclustijd (%)",0.0,0.5,0.08,0.01)
    sd_scrap=st.number_input("σ scrap (additief)",0.0,0.5,0.01,0.005)
    mc_samples=None
    if mc_on:
        mc_samples=run_mc(st.session_state["routing_df"], st.session_state["bom_df"], Q, netkg, price, sd_mat, sd_cycle, sd_scrap, iters,
                          energy=energy,labor=LABOR,mrates=MACHINE_RATES,storage_days=storage_days,storage_cost=storage_cost,km=km,eur_km=eur_km,rework=rework,rework_min=rework_min)
        st.plotly_chart(px.histogram(pd.DataFrame({"UnitCost":mc_samples}), x="UnitCost", nbins=40), use_container_width=True)

# Capaciteit
st.subheader("Capaciteit")
hours_day=st.number_input("Uren productie per dag",1.0,24.0,8.0,0.5)
with st.expander("Capaciteit per proces (h/dag)"):
    cap_proc={p: st.number_input(f"{p}",0.0,24.0,8.0,key=f"cap_{p}") for p in MACHINE_RATES}
cap_df=capacity_table(st.session_state["routing_df"], Q, hours_day, cap_proc)
if not cap_df.empty:
    show=cap_df.copy(); show["Util_%"]=(show["Util_pct"]*100).round(1)
    st.dataframe(show,use_container_width=True)

# Session doorgeven aan Rapport
st.session_state.update({"project":project,"Q":Q,"mat":mat,"netkg":netkg,"price":price,"price_src":src,"res":res,"mc_samples":mc_samples,"cap_df":cap_df})
