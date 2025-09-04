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
# pages/11_Rollen_Branding.py
import os, sys, io, textwrap
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

import streamlit as st
st.set_page_config(page_title="Rollen & Branding", page_icon="🎛️", layout="wide")
st.title("🎛️ Rollen & Branding")

st.caption("Stel een **klantmodus** in (gestripte UI, geen gevoelige knoppen) en pas **branding** aan (logo, accentkleur, disclaimers).")

# -----------------------
# Rolkeuze
# -----------------------
role = st.radio("Applicatie modus", ["Intern (volledig)","Klant (beperkt)"], horizontal=True,
                index=0 if st.session_state.get("app_role","intern")=="intern" else 1)

st.session_state["app_role"] = "intern" if role.startswith("Intern") else "klant"

st.info(f"Huidige rol: **{st.session_state['app_role']}**. Je kunt in de andere pagina's checks doen op deze vlag om knoppen/secties te verbergen.")

# -----------------------
# Branding
# -----------------------
st.subheader("Branding")
col1, col2 = st.columns([1,2])
with col1:
    logo = st.file_uploader("Logo upload (PNG/JPG)", type=["png","jpg","jpeg"])
    dark_mode = st.checkbox("Donkere modus voorkeur", value=st.session_state.get("brand_dark", False))
with col2:
    primary = st.color_picker("Accentkleur (primaryColor)", value=st.session_state.get("brand_primary","#F63366"))
    accent  = st.color_picker("Secundaire kleur (optioneel)", value=st.session_state.get("brand_accent","#0E1117"))

st.session_state["brand_primary"] = primary
st.session_state["brand_accent"]  = accent
st.session_state["brand_dark"]    = dark_mode

# Snelle CSS-injectie (runtime, niet persistent)
css = f"""
<style>
:root {{
  --primary-color: {primary};
}}
.block-container h1, .block-container h2, .block-container h3 {{
  letter-spacing: 0.1px;
}}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# Toon logo (in-memory)
if logo:
    st.image(logo, caption="Logo (runtime)")

st.markdown("---")
st.subheader("Disclaimer & Voettekst")
disclaimer = st.text_area("Disclaimer tekst (wordt bij Rapport gebruikt als voetnoot)",
                          value=st.session_state.get("brand_disclaimer",
                          "Deze calculatie is indicatief en onder voorbehoud van materiaal- en energietarieven."))
st.session_state["brand_disclaimer"] = disclaimer

st.success("Brandingvoorkeuren staan nu in `st.session_state`. Je kunt ze in andere pagina's uitlezen.")

# -----------------------
# Genereer .streamlit/config.toml
# -----------------------
st.markdown("### Genereer Streamlit config (permanent thema)")
config = textwrap.dedent(f"""
    [theme]
    base = "{'dark' if dark_mode else 'light'}"
    primaryColor = "{primary}"
    """).strip()

st.code(config, language="toml")
st.download_button("⬇️ Download config.toml", config.encode("utf-8"),
                   "config.toml","text/plain")

st.caption("""
Plaats dit bestand in je repo onder **`.streamlit/config.toml`** om het thema **permanent** te maken.
Runtime-CSS hierboven blijft alleen voor de huidige sessie.
""")

# -----------------------
# Voorbeeld: rol-guard snippet
# -----------------------
st.markdown("### Voorbeeld: UI verbergen in klantmodus")
st.code(
"""
# in andere pagina's:
if st.session_state.get("app_role") == "klant":
    with st.expander("🔒 Interne opties (verborgen voor klant)", expanded=False):
        st.info("Niet beschikbaar in klantmodus.")
else:
    st.button("Interne knop: GitHub push / presets / debug")
""",
language="python")
