from bootstrap import configure_page, init_state
from utils.safe import run_safely
from utils.io import read_csv_safe, SCHEMA_PROCESSES, paths
from utils.costing import machine_cost_per_hour, labor_cost_per_hour
import streamlit as st

configure_page(); init_state()
st.title("Routing Kosten - PLUS")

p = paths()["processes"]
df = run_safely("Load processes", read_csv_safe, p, SCHEMA_PROCESSES)
if df is None:
    st.stop()

st.subheader("Basis tarieven (CSV)")
st.dataframe(df[["process_id","machine_rate_eur_h","labor_rate_eur_h","overhead_pct","margin_pct"]].fillna(""),
             use_container_width=True)

st.sidebar.header("Machine uurkosten (model)")
capex = st.sidebar.number_input("CAPEX (EUR)", min_value=0.0, value=120000.0, step=5000.0)
life  = st.sidebar.number_input("Levensduur (jaar)", min_value=1.0, value=7.0, step=0.5)
util  = st.sidebar.number_input("Bezettingsgraad (0-1)", min_value=0.05, max_value=1.0, value=0.65, step=0.05)
maint = st.sidebar.number_input("Onderhoud % CAPEX", min_value=0.0, max_value=1.0, value=0.05, step=0.01)
ekwh  = st.sidebar.number_input("Energie (EUR/kWh)", min_value=0.0, value=0.25, step=0.01)
kwh   = st.sidebar.number_input("Verbruik (kWh/uur)", min_value=0.0, value=8.0, step=0.5)

model_rate = machine_cost_per_hour(capex, life, util, maint, ekwh, kwh)
st.info(f"Model: machine-uurkosten ~ EUR {model_rate:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))

st.sidebar.header("Arbeid")
hr = st.sidebar.number_input("Bruto uurloon", min_value=0.0, value=40.0, step=1.0)
oh = st.sidebar.number_input("Overhead %", min_value=0.0, max_value=1.0, value=0.2, step=0.05)
mg = st.sidebar.number_input("Marge %",   min_value=0.0, max_value=1.0, value=0.1, step=0.05)
lrate = labor_cost_per_hour(hr, oh, mg)
st.info(f"Model: labor-uurkosten ~ EUR {lrate:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
