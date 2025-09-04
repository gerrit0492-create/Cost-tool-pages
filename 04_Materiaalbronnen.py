from bootstrap import configure_page, init_state
configure_page(); init_state()

import streamlit as st
import pandas as pd
from pathlib import Path


st.title("📡 Materiaalprijzen & bronnen")

def load_materials_any():
    # 1) Nieuw schema (aanbevolen)
    p_new = Path("data/materials_db.csv")
    if p_new.exists():
        df = pd.read_csv(p_new)
        if "material_id" in df.columns:
            return df, "materials_db.csv"
    # 2) Oud schema (compat)
    p_old = Path("data/material_prices.csv")
    if p_old.exists():
        df = pd.read_csv(p_old)
        # map minimaal naar nieuw
        # verwacht minstens: material_id, grade, price_eur_per_kg
        for col in ["material_id","grade","en_number","category","form","density_kg_per_m3",
                    "price_eur_per_kg","price_source","source_url","source_date","scrap_pct","yield_loss_pct","notes"]:
            if col not in df.columns:
                df[col] = None
        return df, "material_prices.csv"
    # 3) Leeg
    cols = ["material_id","grade","en_number","category","form","density_kg_per_m3",
            "price_eur_per_kg","price_source","source_url","source_date","scrap_pct","yield_loss_pct","notes"]
    return pd.DataFrame(columns=cols), "(new)"

materials_df, origin = load_materials_any()
st.caption(f"Bronbestand gedetecteerd: **{origin}**")

# Upload van bijgewerkte prijzen
up = st.file_uploader("Upload bijgewerkte materialen-CSV (zelfde kolommen)", type=["csv"])
if up:
    new = pd.read_csv(up)
    key = "material_id"
    base = materials_df.drop(columns=[c for c in ["price_eur_per_kg","price_source","source_url","source_date"] if c in materials_df.columns], errors="ignore")
    merged = base.merge(new[[key,"price_eur_per_kg","price_source","source_url","source_date"]], on=key, how="left")
    materials_df = merged
    st.success("Upload toegepast.")

# Overrides per materiaal
with st.expander("Snel override instellen (€/kg + bron + datum)"):
    if len(materials_df) == 0:
        st.info("Geen materialen aanwezig. Upload of werk je CSV bij.")
    else:
        mid = st.selectbox("Materiaal", materials_df["material_id"].dropna().unique().tolist())
        eurkg = st.number_input("€/kg", min_value=0.0, step=0.1, value=float(materials_df.loc[materials_df.material_id==mid,"price_eur_per_kg"].dropna().head(1).fillna(0).values[0]) if (materials_df.material_id==mid).any() else 0.0)
        src = st.text_input("Bron (bijv. MCB prijsblad week 35)")
        sdt = st.text_input("Datum (YYYY-MM-DD)")
        if st.button("Override toepassen"):
            ix = materials_df.material_id == mid
            materials_df.loc[ix, "price_eur_per_kg"] = eurkg
            materials_df.loc[ix, "price_source"] = src
            materials_df.loc[ix, "source_date"] = sdt
            st.success(f"Override toegepast op {mid}")

# Output tonen
show_cols = ["material_id","grade","en_number","category","form","price_eur_per_kg","price_source","source_date","scrap_pct","yield_loss_pct"]
exists = [c for c in show_cols if c in materials_df.columns]
st.dataframe(materials_df[exists], use_container_width=True)

# Download resolved
st.download_button(
    "⬇️ Export: materials_resolved.csv",
    data=materials_df.to_csv(index=False).encode("utf-8"),
    file_name="materials_resolved.csv",
    mime="text/csv"
)

st.caption("Tip: wil je volledig schema? Gebruik materials_db.csv (nieuw).")
