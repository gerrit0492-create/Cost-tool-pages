import streamlit as st, json, os
st.set_page_config(page_title="BOM import", page_icon="📥", layout="wide")
st.title("📥 BOM import (JSON)")

txt = st.text_area("Plak je BOM JSON (van { tot })", height=260, placeholder='{"bom":[...], "assembly":{"name":"...", "qty":50}}')
if st.button("Opslaan"):
    try:
        data = json.loads(txt)
        os.makedirs("data", exist_ok=True)
        with open("data/bom_current.json","w") as f:
            json.dump(data, f, indent=2)
        st.success("BOM opgeslagen → data/bom_current.json")
    except Exception as e:
        st.error(f"JSON fout: {e}")
