import json, os
import streamlit as st

st.set_page_config(page_title="BOM import", page_icon="📦", layout="wide")
st.title("📦 BOM import — veilig opslaan (geen leeg wegschrijven)")

BOM_PATH = "data/bom_current.json"

# --- Helpers
def read_file_text(path: str) -> str:
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

def validate_bom_json(txt: str):
    """Parse en basisvalidatie. Retourneert (ok, parsed|fouttekst)."""
    try:
        data = json.loads(txt)
    except Exception as e:
        return False, f"JSON parse error: {e}"
    if not isinstance(data, dict):
        return False, "Root moet een JSON-object zijn { ... }."
    if "bom" not in data or not isinstance(data["bom"], list):
        return False, "Veld 'bom' ontbreekt of is geen lijst."
    return True, data

# --- Laad huidige bestandstekst + last-good
if "last_good_bom" not in st.session_state:
    # probeer huidige file als “last good” te zetten
    raw = read_file_text(BOM_PATH).strip()
    ok, val = validate_bom_json(raw) if raw else (False, None)
    if ok:
        st.session_state.last_good_bom = val
    else:
        st.session_state.last_good_bom = None

current_text = read_file_text(BOM_PATH).strip()

colL, colR = st.columns([3, 1])
with colR:
    st.markdown("### Acties")
    load_example = st.button("📋 Voorbeeld laden")
    restore_last = st.button("🛟 Herstel laatste geldige")
    save_btn     = st.button("💾 Opslaan")

# Voorbeeld-BOM (je zware as)
example_json = {
  "bom": [
    {
      "item_code": "Shaft-370x6000",
      "description": "Duplex shaft Ø370 L6000, taper L500 to Ø210, center bore Ø95 L5000",
      "material_grade": "1.4462",
      "material_family": "duplex",
      "form": "bar",
      "diameter_mm": 370,
      "length_mm": 6000,
      "thickness_mm": None,
      "width_mm": None,
      "qty": 1,
      "processes": ["CNC_turn", "taper_turn", "drill_bore", "deburr"],
      "notes": "Taper aan één zijde; axiale centerboor"
    }
  ],
  "assembly": { "name": "Pilot-Assembly-Shaft", "qty": 1 }
}

# Bepaal initiële textarea-inhoud
if load_example:
    initial_text = json.dumps(example_json, indent=2)
elif restore_last and st.session_state.last_good_bom:
    initial_text = json.dumps(st.session_state.last_good_bom, indent=2)
else:
    # toon bestaand bestand; als dat kapot is, toon lege maar schrijf NIET weg
    initial_text = current_text if current_text else json.dumps(example_json, indent=2)

with colL:
    st.caption("Plak hieronder **pure JSON** (alleen van `{` tot `}`), geen markdown of 'Bronnen'.")
    txt = st.text_area("BOM JSON", value=initial_text, height=420, label_visibility="collapsed")

# --- Opslaan: alleen als SAVE is geklikt én JSON geldig is
if save_btn:
    raw = (txt or "").strip()
    ok, val = validate_bom_json(raw)
    if not ok:
        st.error(f"Niet opgeslagen. {val}")
    else:
        os.makedirs("data", exist_ok=True)
        with open(BOM_PATH, "w", encoding="utf-8") as f:
            json.dump(val, f, indent=2)
        st.session_state.last_good_bom = val
        st.success("BOM opgeslagen ✅")
        st.rerun()

# --- Preview (schrijft niets)
ok, val = validate_bom_json((txt or "").strip())
if ok:
    st.success("Voorvertoning: JSON is geldig.")
    st.json(val)
else:
    st.warning("JSON is (nog) niet geldig. Pas aan en klik daarna **Opslaan**.")
