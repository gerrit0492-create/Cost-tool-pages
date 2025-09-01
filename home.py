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
import streamlit as st

st.write("✅ App is gestart")
import streamlit as st
st.set_page_config(page_title="Maakindustrie Cost Tool", page_icon="🧮", layout="wide")

st.title("🧮 Maakindustrie Cost Tool")
st.write("""
Welkom! Gebruik het menu links:
- **Calculatie** – invoer, routing/BOM, berekening, Monte-Carlo, capaciteit, export (Excel/CSV/Power BI).
- **Rapport** – klant-PDF met grafieken op basis van de laatste calculatie.
""")
st.info("Tip: voer eerst een calculatie uit; het Rapport gebruikt die gegevens uit de session state.")
