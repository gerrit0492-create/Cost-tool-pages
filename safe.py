from __future__ import annotations
import streamlit as st
from typing import Callable, Any

def run_safely(label: str, fn: Callable[..., Any], *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        st.error(f"{label} faalde: {type(e).__name__}: {e}")
        return None

def guard(fn: Callable[[], Any]) -> None:
    try:
        fn()
    except Exception as e:
        st.error(f"Deze page kon niet starten: {type(e).__name__}: {e}")
        st.stop()
