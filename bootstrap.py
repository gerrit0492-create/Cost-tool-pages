# bootstrap.py
import streamlit as st

def configure_page():
    st.set_page_config(page_title="Maakindustrie Cost Tool", page_icon="📦", layout="wide")

def init_state():
    ss = st.session_state
    ss.setdefault("bom", None)              # pandas.DataFrame
    ss.setdefault("materials", None)        # pandas.DataFrame
    ss.setdefault("processes", None)        # pandas.DataFrame (optioneel)
    ss.setdefault("price_overrides", {})    # {material_id: {eur_per_kg, source, date}}
