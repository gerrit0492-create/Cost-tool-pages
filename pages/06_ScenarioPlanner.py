# pages/06_ScenarioPlanner.py
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

import streamlit as st, pandas as pd, numpy as np
from utils.shared import (MATERIALS, MACHINE_RATES, LABOR, cost_once, run_mc)

st.set_page_config(page_title="Scenario Planner", page_icon="🧭", layout="wide")
st.title("🧭 Scenario Planner")

# Basisbron uit huidige sessie
routing = st.session_state.get("routing_df")
bom     = st.session_state.get("bom_df")
defaults = dict(
    Q=st.session_state.get("Q", 50),
    netkg=st.session_state.get("netkg", 2.0),
    price=st.session_state.get("price", 3.50),
    energy=st.session_state.get("energy", 0.20),
    storage_days=st.session_state.get("storage_days", 0.0),
    storage_cost=st.session_state.get("storage_cost", 0.0),
    km=st.session_state.get("km", 0.0), eur_km=st.session_state.get("eur_km",0.0),
    rework=st.session_state.get("rework",0.0), rework_min=st.session_state.get("rework_min",0.0)
)
if routing is None or bom is None:
    st.warning("Ga eerst naar **01_Calculatie** en voer een basis-invoer uit.")
    st.stop()

st.caption("Definieer scenario’s. Cycle- en scrapfactor schalen de routing (1.10 = +10%).")

N = st.number_input("Aantal scenario’s", 1, 10, 3)
rows=[]
for i in range(N):
    with st.expander(f"Scenario {i+1}", expanded=(i==0)):
        col1,col2,col3,col4 = st.columns(4)
        Q         = col1.number_input("Q", 1, 100000, defaults["Q"], key=f"Q_{i}")
        price     = col2.number_input("Materiaal €/kg", 0.0, 100.0, defaults["price"], 0.01, key=f"price_{i}")
        cyc_fac   = col3.number_input("Cycle factor", 0.1, 5.0, 1.0, 0.05, key=f"cyc_{i}")
        scrap_fac = col4.number_input("Scrap factor", 0.1, 5.0, 1.0, 0.05, key=f"scr_{i}")
        # MC optioneel
        mcc1, mcc2, mcc3 = st.columns(3)
        mc_on  = mcc1.checkbox("Monte-Carlo", False, key=f"mc_{i}")
        iters  = mcc2.number_input("Iteraties", 100, 20000, 1000, 100, key=f"it_{i}")
        sigma  = mcc3.number_input("σ% (cycle & mat)", 0.0, 0.5, 0.08, 0.01, key=f"sg_{i}")

        r = pd.DataFrame(routing).copy()
        if "Cycle_min" in r: r["Cycle_min"] = r["Cycle_min"]*cyc_fac
        if "Scrap_pct" in r: r["Scrap_pct"] = (r["Scrap_pct"]*scrap_fac).clip(0.0, 0.35)
        res = cost_once(r, pd.DataFrame(bom), Q, defaults["netkg"], price,
                        defaults["energy"], LABOR, MACHINE_RATES,
                        defaults["storage_days"], defaults["storage_cost"],
                        defaults["km"], defaults["eur_km"], defaults["rework"], defaults["rework_min"])
        row = {"Scenario": i+1, "Q": Q, "€/kg": price,
               "Mat_pc": res["mat_pc"], "Conv": res["conv_total"], "Lean": res["lean_total"],
               "Buy": res["buy_total"], "UnitCost": res["total_pc"]}
        if mc_on:
            samples = run_mc(r, pd.DataFrame(bom), Q, defaults["netkg"], price,
                             sigma, sigma, sigma/8.0, iters=iters,
                             energy=defaults["energy"], labor=LABOR, mrates=MACHINE_RATES,
                             storage_days=defaults["storage_days"], storage_cost=defaults["storage_cost"],
                             km=defaults["km"], eur_km=defaults["eur_km"], rework=defaults["rework"], rework_min=defaults["rework_min"])
            row.update({"P50": float(np.percentile(samples,50)),
                        "P80": float(np.percentile(samples,80)),
                        "P95": float(np.percentile(samples,95))})
        rows.append(row)

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True)
if not df.empty:
    st.bar_chart(df.set_index("Scenario")[["UnitCost"]])
    st.download_button("⬇️ Export (CSV)", df.to_csv(index=False).encode("utf-8"),
                       "scenario_results.csv","text/csv")
