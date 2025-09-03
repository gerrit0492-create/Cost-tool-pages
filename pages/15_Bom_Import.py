from bootstrap import configure_page, init_state
configure_page(); init_state()

import streamlit as st
import pandas as pd

BOM_COLS = ["item_no","parent","part_no","description","material_id","qty","uom",
            "length_mm","width_mm","thickness_mm","diameter_mm","height_mm",
            "mass_kg","process_route","tolerance_class","surface_ra_um","heat_treat","notes"]

st.title("📥 BOM import")

up = st.file_uploader("Upload BOM CSV (zie template-kolommen)", type=["csv"])
if up:
    try:
        df = pd.read_csv(up)
        missing = [c for c in BOM_COLS if c not in df.columns]
        if missing:
            st.error(f"Ontbrekende kolommen: {', '.join(missing)}")
        else:
            st.session_state["bom"] = df[BOM_COLS]
            st.success(f"{len(df)} regels geladen en persistent in session_state ✅")
    except Exception as e:
        st.exception(e)

bom = st.session_state.get("bom")
if bom is not None and len(bom):
    st.subheader("Huidige BOM")
    st.dataframe(bom, use_container_width=True)
    st.download_button(
        "⬇️ Export huidige BOM",
        data=bom.to_csv(index=False).encode("utf-8"),
        file_name="bom_current.csv",
        mime="text/csv"
    )
else:
    st.info("Nog geen BOM geladen. Gebruik de template om te starten.")
