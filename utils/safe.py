from __future__ import annotations
import traceback
import streamlit as st

def run_safely(label: str, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        st.error(f"{label} failed")
        st.exception(e)
        traceback.print_exc()
        return None
