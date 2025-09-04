# bovenin elk .py bestand
import streamlit as st, traceback

def guard(run):
    try:
        run()
    except Exception:
        err = traceback.format_exc()
        # toon in UI
        st.exception(err)
        # bewaar ook in session_state zodat Diagnose-pagina hem kan tonen
        st.session_state["last_exception"] = err
