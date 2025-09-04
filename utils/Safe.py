# utils/safe.py
from __future__ import annotations
import streamlit as st
from typing import Callable, Any

def run_safely(label: str, fn: Callable[..., Any], *args, **kwargs):
    """Voer een functie uit en toon nette foutmeldingen in Streamlit i.p.v. hard crashen."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        st.error(f"{label} faalde: {type(e).__name__}: {e}")
        return None

def guard(fn: Callable[[], Any]) -> None:
    """Voorkom dat een page de hele app breekt."""
    try:
        fn()
    except Exception as e:
        st.error(f"Deze page kon niet starten: {type(e).__name__}: {e}")
        st.stop()
