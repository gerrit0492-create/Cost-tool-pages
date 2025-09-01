# pages/07_SupplierQuotes.py
import os, sys, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

import streamlit as st, pandas as pd

st.set_page_config(page_title="Supplier Quotes", page_icon="📦", layout="wide")
st.title("📦 Supplier Quotes")

if "quotes_df" not in st.session_state:
    st.session_state["quotes_df"] = pd.DataFrame(
        [{"Supplier":"DemoSteel BV","Item":"S235 plaat 5mm","UoM":"€/kg","Price":1.35,"ValidUntil":(dt.date.today()+dt.timedelta(days=30)).isoformat(),"Notes":"excl. transport"},
         {"Supplier":"AluCo","Item":"6060 T66 extrusie","UoM":"€/kg","Price":3.10,"ValidUntil":(dt.date.today()+dt.timedelta(days=20)).isoformat(),"Notes":""}]
    )

st.caption("Voeg leveranciers aan, beheer geldigheid en koppel aan BOM posities.")

st.subheader("Quotes beheren")
st.session_state["quotes_df"] = pd.DataFrame(st.data_editor(
    st.session_state["quotes_df"], num_rows="dynamic", use_container_width=True
))
qdf = st.session_state["quotes_df"]

col1,col2 = st.columns(2)
with col1:
    st.download_button("⬇️ Download quotes (CSV)", qdf.to_csv(index=False).encode("utf-8"),
                       "supplier_quotes.csv","text/csv")
with col2:
    up = st.file_uploader("Upload quotes CSV", type=["csv"])
    if up:
        try:
            st.session_state["quotes_df"] = pd.read_csv(up)
            st.success("Quotes geladen.")
        except Exception as e:
            st.error(f"Kon CSV niet lezen: {e}")

st.markdown("---")
st.subheader("Koppelen aan BOM (optioneel)")

bom = st.session_state.get("bom_df")
if bom is None or len(bom)==0:
    st.info("Geen BOM in sessie. Ga naar **01_Calculatie**.")
else:
    bom = pd.DataFrame(bom).copy()
    if "Supplier" not in bom.columns:
        bom["Supplier"] = ""
    st.write("**BOM**")
    st.dataframe(bom, use_container_width=True)

    # Suggestie: match per Item string
    if st.button("🔗 Suggestie: match op Item-string"):
        suggestions = []
        for i, row in bom.iterrows():
            item = str(row.get("Part","")).lower()
            match = qdf[qdf["Item"].str.lower().str.contains(item, na=False)]
            sup = match.iloc[0]["Supplier"] if not match.empty else ""
            suggestions.append(sup)
        bom["Supplier"] = suggestions
        st.session_state["bom_df"] = bom
        st.success("Suggesties toegepast (controleer handmatig).")

st.markdown("---")
st.subheader("Trends & Geldigheid")

if not qdf.empty:
    qdf["ValidUntil_dt"] = pd.to_datetime(qdf["ValidUntil"], errors="coerce")
    expiring = qdf[qdf["ValidUntil_dt"] <= (pd.Timestamp.today() + pd.Timedelta(days=14))]
    if not expiring.empty:
        st.warning(f"{len(expiring)} quotes verlopen binnen 14 dagen.")
        st.dataframe(expiring[["Supplier","Item","Price","ValidUntil"]], use_container_width=True)
