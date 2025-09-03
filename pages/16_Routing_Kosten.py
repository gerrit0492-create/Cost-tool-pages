# pages/16_Routing_Kosten.py  (v2: veilige BOM-load, duplex-dichtheid, slimme tariefmapping)
import os, json, math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Routing & Kosten", page_icon="🛠️", layout="wide")
st.title("🛠️ Routing & kosten (v2) — duplex aware + veilige BOM-inleeslogica")

# ---------- Helpers
DENSITY_KG_PER_MM3 = {
    "stainless": 7.9e-6,
    "duplex":    7.8e-6,   # 1.4462 / 2205
    "aluminum":  2.7e-6,
    "carbon_steel": 7.85e-6,
}

def infer_family_from_grade(grade: str) -> str:
    g = (grade or "").lower()
    # duplex markers
    if "1.4462" in g or "2205" in g or "s31803" in g or "s32205" in g:
        return "duplex"
    # rvs austenitisch
    if any(k in g for k in ["304", "316", "1.43", "1.45"]):
        return "stainless"
    # aluminium
    if any(k in g for k in ["6082", "6061", "5754", "1050", "alu", "aluminium"]):
        return "aluminum"
    return "carbon_steel"

def latest_material_price(df_prices, grade, region="EU", unit="€/kg"):
    if df_prices.empty:
        return None
    d = df_prices.copy()
    d = d[d["grade"].astype(str).str.lower() == str(grade).lower()]
    if region:
        d = d[d["region"].astype(str).str.upper() == str(region).upper()]
    if unit:
        d = d[d["unit"].astype(str) == unit]
    if d.empty:
        return None
    d["as_of_date"] = pd.to_datetime(d["as_of_date"], errors="coerce")
    d = d.sort_values("as_of_date")
    return float(d.iloc[-1]["price"])

def midpoint_rate(df_rates, process_kw, country="Netherlands"):
    if df_rates.empty:
        return None
    d = df_rates.copy()
    d = d[d["process"].astype(str).str.lower().str.contains(process_kw.lower())]
    if not d.empty:
        d2 = d[d["country"].astype(str).str.lower() == country.lower()]
        if not d2.empty:
            d = d2
    if d.empty:
        return None
    d["as_of_date"] = pd.to_datetime(d["as_of_date"], errors="coerce")
    r = d.sort_values("as_of_date").iloc[-1]
    return float((r["rate_min"] + r["rate_max"]) / 2.0) / 60.0  # €/min

def map_rate_for_process(df_rates, proc_name: str):
    """
    Slimme tariefmapping.
    Ondersteund: laser, bend, TIG, CNC_mill, CNC_turn, taper_turn, drill_bore, deburr (fallbacks).
    """
    p = (proc_name or "").strip().lower()
    direct_map = {
        "laser": ["laser", "lasersnijden"],
        "bend": ["bend", "buigen", "kantbank", "press brake"],
        "tig": ["tig", "tig welding", "lassen tig"],
        "cnc_mill": ["cnc mill", "cnc milling", "frezen"],
        "cnc_turn": ["cnc turn", "cnc turning", "draaien"],
        "taper_turn": ["taper turn", "taper turning", "conisch draaien"],
        "drill_bore": ["drill", "deep drill", "boren", "gun drill", "drill bore"],
        "deburr": ["deburr", "afbramen"]
    }
    # probeer directe/synoniem hits, met mapping naar dichtstbijzijnde algemene categorie
    for key, kws in direct_map.items():
        if p == key or any(p == k or p in k for k in kws):
            if key == "laser":
                return midpoint_rate(df_rates, "laser") or midpoint_rate(df_rates, "cnc milling")
            if key == "bend":
                return midpoint_rate(df_rates, "cnc milling")
            if key == "tig":
                return midpoint_rate(df_rates, "tig")
            if key == "cnc_mill":
                return midpoint_rate(df_rates, "cnc milling")
            if key in ["cnc_turn", "taper_turn"]:
                return midpoint_rate(df_rates, "cnc turning") or midpoint_rate(df_rates, "cnc")
            if key == "drill_bore":
                return midpoint_rate(df_rates, "cnc") or midpoint_rate(df_rates, "cnc milling")
            if key == "deburr":
                return midpoint_rate(df_rates, "cnc") or midpoint_rate(df_rates, "cnc milling")
    # ultieme fallback
    return midpoint_rate(df_rates, p) or (1.00/60.0)

def est_process_minutes(part, process):
    """Vuistregels per stuk: cycle + (setup/qty)."""
    q = max(1, int(part.get("qty", 1)))
    p = (process or "").strip().lower()
    base = {
        "laser": (5.0, 0.43),
        "bend": (8.0, 0.50),
        "tig": (10.0, 0.60),
        "cnc_mill": (12.0, 1.20),
        "cnc_turn": (10.0, 1.00),
        "taper_turn": (12.0, 1.30),    # conisch draaien
        "drill_bore": (10.0, 1.10),    # diepboren/gun-drill
        "deburr": (3.0, 0.20)
    }
    setup, cycle = base.get(p, (5.0, 0.30))
    return (setup / q) + cycle

def mass_kg(part):
    """Schat massa op basis van vorm + dichtheid (incl. duplex 7.8e-6)."""
    grade = part.get("material_grade", "")
    fam = (part.get("material_family") or infer_family_from_grade(grade)).lower()
    rho = DENSITY_KG_PER_MM3.get(fam, 7.85e-6)
    form = (part.get("form") or "").lower()
    t = part.get("thickness_mm") or 0
    L = part.get("length_mm") or 0
    W = part.get("width_mm") or 0
    dia = part.get("diameter_mm") or 0

    if form in ("sheet", "plate"):
        vol = float(t) * float(L) * float(W)  # mm^3
    elif form in ("bar", "staf", "round", "rod") and dia and L:
        vol = math.pi * (float(dia)/2)**2 * float(L)
    else:
        vol = float(t) * float(L) * float(W)

    return 0.0 if vol <= 0 else vol * rho  # kg

# ---------- Veilige BOM-inleeslogica
bom_path = "data/bom_current.json"
if not os.path.exists(bom_path):
    st.error("BOM ontbreekt: data/bom_current.json. Ga naar 'BOM import' en sla je BOM op.")
    st.stop()

try:
    with open(bom_path, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    if not raw:
        raise ValueError("Leeg bestand")
    bom_json = json.loads(raw)
except Exception as e:
    st.error(f"BOM niet leesbaar: {e}. Open 'BOM import', plak geldige JSON (alleen van '{{' tot '}}') en sla opnieuw op.")
    st.stop()

bom = bom_json.get("bom", [])

# ---------- Prijslijsten en tarieven
df_prices = pd.read_csv("data/material_prices.csv") if os.path.exists("data/material_prices.csv") else pd.DataFrame()
df_rates  = pd.read_csv("data/labor_rates.csv") if os.path.exists("data/labor_rates.csv") else pd.DataFrame()

# ---------- Reken per item
rows = []
for p in bom:
    item = p.get("item_code", "?")
    qty  = int(p.get("qty", 1))
    grade = p.get("material_grade", "").strip()
    fam   = (p.get("material_family") or infer_family_from_grade(grade)).strip()

    # €/kg (region EU, unit €/kg)
    eurkg = latest_material_price(df_prices, grade=grade, region="EU", unit="€/kg") or 0.0

    # massa & materiaal
    m_kg = mass_kg(p)
    mat_eur_pc = eurkg * m_kg

    # processen
    procs = [x.strip() for x in (p.get("processes") or [])]
    proc_cost_eur_per_pc = 0.0
    det = []
    for proc in procs:
        norm = proc.upper() if proc.upper() == "TIG" else proc.lower()
        rate_eur_min = map_rate_for_process(df_rates, norm) or (1.00/60.0)
        minutes = est_process_minutes(p, norm)
        cost_pc = minutes * rate_eur_min
        proc_cost_eur_per_pc += cost_pc
        det.append(f"{proc}@{rate_eur_min:.2f}€/min × {minutes:.2f} min = €{cost_pc:.2f}")

    total_per_pc = mat_eur_pc + proc_cost_eur_per_pc

    rows.append({
        "item_code": item,
        "qty": qty,
        "material_family": fam,
        "grade": grade,
        "mass_kg_per_pc": round(m_kg, 4),
        "eur_per_kg": round(eurkg, 4),
        "Material €/pc": round(mat_eur_pc, 2),
        "Proc €/pc": round(proc_cost_eur_per_pc, 2),
        "Total €/pc": round(total_per_pc, 2),
        "Processes": " | ".join(det) if det else ""
    })

df = pd.DataFrame(rows)

# ---------- Weergave
st.subheader("Per item")
df_display = df[["item_code","qty","grade","material_family","mass_kg_per_pc","eur_per_kg","Material €/pc","Proc €/pc","Total €/pc"]].copy()
st.dataframe(df_display, use_container_width=True)

tot_value = float((df["Total €/pc"] * df["qty"]).sum()) if not df.empty else 0.0
st.success(f"🌟 Totale waarde (qty × Total €/pc): € {tot_value:,.2f}")

with st.expander("Procesdetails (per item)"):
    for r in rows:
        st.markdown(f"**{r['item_code']}** — {r['Processes'] or '_geen procesregels_'}")

# ---------- Hints / waarschuwingen
missing_prices = [r["grade"] for r in rows if r["eur_per_kg"] == 0.0]
if missing_prices:
    st.warning("Geen €/kg gevonden voor: " + ", ".join(sorted(set(missing_prices))) +
               ". Voeg regels toe in material_prices.csv met region='EU' en unit='€/kg' (en juiste grade).")

# ---------- Download
st.download_button(
    "⬇️ Download resultaten (CSV)",
    df_display.to_csv(index=False),
    file_name="routing_kosten_resultaten.csv",
    mime="text/csv"
)
