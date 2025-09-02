# pages/01_Marktdata.py
import io
import pandas as pd
import streamlit as st
from utils.perplexity_ingest import normalize, save_append_csv, dedupe_latest

st.title("📡 Marktdata import (Perplexity → CSV)")
st.caption("Plak JSON van Perplexity met material_prices en/of labor_rates. We valideren, tonen en slaan op.")

# Invoer
raw = st.text_area(
    "Plak hier de JSON-output van Perplexity",
    height=220,
    placeholder='{"material_prices":[{...}], "labor_rates":[{...}]}'
)

col_a, col_b, col_c = st.columns(3)
do_preview = col_a.button("🔎 Valideren & Preview")
do_save    = col_b.button("💾 Opslaan naar CSV")
do_clear   = col_c.button("🧹 Leeg velden")

if do_clear:
    st.rerun()

# Uitvoer-paden

MAT_PATH = "data/material_prices.csv"
LAB_PATH = "data/labor_rates.csv"

if do_preview or do_save:
    if not raw.strip():
        st.error("Geen JSON geplakt.")
        st.stop()
    try:
        df_m, df_l = normalize(raw)
    except Exception as e:
        st.error(f"JSON niet geldig: {e}")
        st.stop()

    # Preview sectie
    if not df_m.empty:
        st.subheader("📦 Materialen (material_prices)")
        # Dedupe voor nette weergave
        dfm_view = dedupe_latest(
            df_m, keys=["material","grade","form","region","unit","currency"], date_col="as_of_date"
        )
        st.dataframe(dfm_view, use_container_width=True)
        # Download-knop
        buf = io.StringIO()
        dfm_view.to_csv(buf, index=False)
        st.download_button("⬇️ Download material_prices (preview CSV)", buf.getvalue(), "material_prices_preview.csv", "text/csv")

    if not df_l.empty:
        st.subheader("🧑‍🏭 Uurtarieven (labor_rates)")
        dfl_view = dedupe_latest(
            df_l, keys=["process","country","currency","basis"], date_col="as_of_date"
        )
        st.dataframe(dfl_view, use_container_width=True)
        buf2 = io.StringIO()
        dfl_view.to_csv(buf2, index=False)
        st.download_button("⬇️ Download labor_rates (preview CSV)", buf2.getvalue(), "labor_rates_preview.csv", "text/csv")

    if df_m.empty and df_l.empty:
        st.warning("Geen material_prices of labor_rates gevonden in je JSON.")
        st.stop()

    # Opslaan
    if do_save:
        try:
            save_append_csv(df_m, MAT_PATH)
            save_append_csv(df_l, LAB_PATH)
            st.success("✅ Opgeslagen. Kijk links in je menu waar deze data wordt gebruikt.")
            if not df_m.empty:
                st.caption(f"📁 Wegschreven naar {MAT_PATH}")
            if not df_l.empty:
                st.caption(f"📁 Wegschreven naar {LAB_PATH}")
        except Exception as e:
            st.error(f"Opslaan mislukte: {e}")
