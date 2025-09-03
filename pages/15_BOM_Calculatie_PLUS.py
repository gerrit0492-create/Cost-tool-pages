from bootstrap import configure_page, init_state
from utils.safe import run_safely
from utils.io import read_csv_safe, SCHEMA_BOM, SCHEMA_MATERIALS, paths
from utils.costing import part_cost
import streamlit as st, pandas as pd

configure_page(); init_state()
st.title("BOM Calculatie - PLUS")

P = paths()
materials = run_safely("Load materials", read_csv_safe, P["materials"], SCHEMA_MATERIALS)
if materials is None:
    st.stop()

up = st.file_uploader("Upload BOM CSV (of gebruik data/bom_template.csv)", type=["csv"])
if up:
    bom = run_safely("Read uploaded BOM", pd.read_csv, up)
else:
    bom = run_safely("Read BOM template", read_csv_safe, P["bom"], SCHEMA_BOM)
if bom is None:
    st.stop()

needed = ["material_id","qty","mass_kg","process_route"]
missing = [c for c in needed if c not in bom.columns]
if missing:
    st.error("Ontbrekende BOM kolommen: " + ", ".join(missing))
    st.stop()

view = bom.merge(materials[["material_id","price_eur_per_kg"]], on="material_id", how="left")

st.sidebar.header("Aannames (demo)")
lt_per_qty = st.sidebar.number_input("Arbeidstijd per qty (uur)", min_value=0.0, value=0.1, step=0.05)
mt_per_qty = st.sidebar.number_input("Machinetijd per qty (uur)", min_value=0.0, value=0.05, step=0.05)
machine_rate = st.sidebar.number_input("Machine rate (EUR/h)", min_value=0.0, value=80.0, step=5.0)
labor_rate   = st.sidebar.number_input("Labor rate (EUR/h)",   min_value=0.0, value=45.0, step=5.0)

def calc_row(r):
    mk = (r.get("mass_kg") or 0.0)
    qty = (r.get("qty") or 0.0)
    price = (r.get("price_eur_per_kg") or 0.0)
    lt = qty * lt_per_qty
    mt = qty * mt_per_qty
    return part_cost(mk, price, mt, machine_rate, lt, labor_rate)

view["part_cost_eur"] = view.apply(calc_row, axis=1)
totals = float(view["part_cost_eur"].sum())
txt = f"Totaal kostprijs (demo): EUR {totals:,.2f}".replace(",", "X").replace(".", ",").replace("X",".")
st.success(txt)
st.dataframe(view, use_container_width=True)
