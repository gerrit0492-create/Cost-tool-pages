from bootstrap import configure_page, init_state
from utils.safe import run_safely
from utils.io import read_csv_safe, SCHEMA_PROCESSES, paths
import streamlit as st, pandas as pd

configure_page(); init_state()
st.title("Scenario Planner - PLUS")

df = run_safely("Load processes", read_csv_safe, paths()["processes"], SCHEMA_PROCESSES)
if df is None:
    st.stop()

m_mult = st.sidebar.number_input("Machine multiplier", min_value=0.0, value=1.15, step=0.05)
l_mult = st.sidebar.number_input("Labor multiplier",   min_value=0.0, value=1.05, step=0.05)

out = df.copy()
if "machine_rate_eur_h" in out.columns:
    out["machine_rate_eur_h_scn"] = out["machine_rate_eur_h"] * m_mult
if "labor_rate_eur_h" in out.columns:
    out["labor_rate_eur_h_scn"] = out["labor_rate_eur_h"] * l_mult

st.subheader("Scenario output")
st.dataframe(out, use_container_width=True)

def delta_pct(new, old):
    return ((pd.to_numeric(new, errors="coerce") - pd.to_numeric(old, errors="coerce")) / pd.to_numeric(old, errors="coerce"))*100.0

if "machine_rate_eur_h" in out.columns and "machine_rate_eur_h_scn" in out.columns:
    out["delta_machine_pct"] = delta_pct(out["machine_rate_eur_h_scn"], out["machine_rate_eur_h"]).round(1)
if "labor_rate_eur_h" in out.columns and "labor_rate_eur_h_scn" in out.columns:
    out["delta_labor_pct"] = delta_pct(out["labor_rate_eur_h_scn"], out["labor_rate_eur_h"]).round(1)
