# pages/01_Calculatie.py
from __future__ import annotations
import streamlit as st
import pandas as pd
from utils.safe import guard
from utils.io import (
    SCHEMA_MATERIALS, SCHEMA_PROCESSES, SCHEMA_BOM,
    load_materials, load_processes, load_bom,
)

def main():
    st.set_page_config(page_title="Quick Cost Check", layout="wide")
    st.title("💸 Quick Cost Check")

    # Data laden
    mats = load_materials()
    procs = load_processes()
    bom = load_bom()

    # Basis weergave
    with st.expander("📄 Materials", expanded=False):
        st.dataframe(mats)
    with st.expander("🛠️ Processes", expanded=False):
        st.dataframe(procs)
    with st.expander("🧾 BOM", expanded=False):
        st.dataframe(bom)

    # Merge & berekening
    df = (
        bom.merge(mats, on="material_id", how="left")
           .merge(procs, left_on="process_route", right_on="process_id", how="left")
    )

    # Guard tegen missende kolommen
    required_cols = [
        "mass_kg", "price_eur_per_kg",
        "runtime_h", "machine_rate_eur_h", "labor_rate_eur_h",
        "overhead_pct", "margin_pct",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Ontbrekende kolommen in data: {missing}")
        st.stop()

    df["material_cost"] = df["mass_kg"] * df["price_eur_per_kg"]
    df["process_cost"] = df["runtime_h"] * (df["machine_rate_eur_h"] + df["labor_rate_eur_h"])
    df["overhead"] = (df["material_cost"] + df["process_cost"]) * df["overhead_pct"]
    df["base_cost"] = df["material_cost"] + df["process_cost"] + df["overhead"]
    df["margin"] = df["base_cost"] * df["margin_pct"]
    df["total_cost"] = df["base_cost"] + df["margin"]

    st.subheader("📊 Calculated costs per BOM line")
    st.dataframe(
        df[[
            "material_id", "qty",
            "material_cost", "process_cost",
            "overhead", "margin", "total_cost"
        ]].copy()
    )

    st.metric("📦 Offer total (EUR)", f"{df['total_cost'].sum():,.2f}")

guard(main)
