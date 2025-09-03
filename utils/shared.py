# utils/shared.py
import streamlit as st
import pandas as pd
from pathlib import Path

@st.cache_data
def load_csv(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)

def get_df(name: str, loader):
    if st.session_state.get(name) is None:
        st.session_state[name] = loader()
    return st.session_state[name]
