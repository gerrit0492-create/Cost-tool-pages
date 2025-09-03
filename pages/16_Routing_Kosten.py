# pages/16_Routing_Kosten.py  (complete versie met duplex-dichtheid en slimme mapping)
import json, os, math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Routing & Kosten", page_icon="🛠️", layout="wide")
st.title("🛠️ Routing & kosten (v2) — duplex aware")

# ---------- Helpers
DENSITY_KG_PER_MM3 = {
    "stainless": 7.9e-6,
    "duplex":    7.8e-6,   # <= 1.4462
    "aluminum":  2.7e-6,
    "carbon_steel": 7.85e-6,
}

def infer_family_from_grade(grade: str) -> str:
    """Leid materiaal-familie af uit een grade-tekst."""
    g = (grade or "").lower()
    # duplex markers (2205 / S31803 / S32205 / 1.4462)
    if "1.4462" in g or "2205" in g or "s31803" in g or "s32205" in g:
        return "duplex"
    # rvs austenitisch
    if any(k in g for k in ["304", "316", "1.43", "1.45"]):
        return "stainless"
    # aluminium
    if any(k in g for k in ["6082", "6061", "5754", "1050", "alu", "aluminium"]):
        return "aluminum"
    # fallback
    return "carbon_steel"

def latest_material_price(df_prices, grade, region="EU", unit="€/kg"):
    if df_prices.empty:
        return None
    d = df_prices.copy()
    # zachte maar doelgerichte filters
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
    """Neem midden van min/max voor proces; match op keyword en land indien aanwezig."""
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
    Ondersteund: laser, bend, TIG, CNC_mill, CNC_turn, taper_turn, drill_bore, deburr (fallback).
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
    # Probeer exacte / synoniemen
    for key, kws in direct_map.items():
        if p == key or any(p == k or p in k for k in kws):
            for kw in [p] + kws:
                # mapping naar “dichtstbijzijnde” algemene categorie
                if key in ["laser"]:
                    r = midpoint_rate(df_rates, "laser") or midpoint_rate(df_rates, "cnc milling")
                elif key in ["bend"]:
                    r = midpoint_rate(df_rates, "cnc milling")
                elif key in ["tig"]:
                    r = midpoint_rate(df_rates, "tig")
                elif key in ["cnc_mill"]:
                    r = midpoint_rate(df_rates, "cnc milling")
                elif key in ["cnc_turn", "taper_turn"]:
                    r = midpoint_rate(df_rates, "cnc turning") or midpoint_rate(df_rates, "cnc")
                elif key in ["drill_bore"]:
                    r = midpoint_rate(df_rates, "cnc") or midpoint_rate(df_rates, "cnc milling")
                elif key in ["deburr"]:
                    r = midpoint_rate(df_rates, "cnc") or midpoint_rate(df_rates, "cnc milling")
                else:
                    r = midpoint_rate(df_rates, kw)
                if r:
                    return r
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
        "taper_turn": (12.0, 1.30),    # conisch draaien wat zwaarder
        "drill_bore": (10.0, 1.10),    # diepboren/gun-drill indicatief
        "deburr": (3.0, 0.20)
    }
    setup, cycle = base.get(p, (5.0, 0.30))
    return (setup / q) + cycle

def mass_kg(part):
    """Schat massa op basis van vorm + dichtheid (duplex 7.8e-6 enz.)."""
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
        # fallback klein prisma
        vol = float(t) * float(L) * float(W)

    if vol <= 0:
        return 0.0
    return vol * rho  # kg

# ---------- Data laden
if not os.path.exists("data/bom_current.json"):
    st.warning("Geen BOM gevonden. Ga eerst naar 'BOM import'.")
    st.stop()

bom = json.load(open("data/bom_current.json")).get("bom", [])
df_prices = pd.read_csv("data/material_prices.csv") if os.path.exists("data/material_prices.csv") else pd.DataFrame()
df_rates  = pd.read_csv("data/labor_rates.csv") if os.path.exists("data/labor_rates.csv") else pd.DataFrame()

# ---------- Reken per item
rows = []
for p in bom:
    item = p.get("item_code", "?")
    qty  = int(p.get("qty", 1))
    grade = p.get("material_grade", "").strip()
    fam   = (p.get("material_family") or infer_family_from_grade(grade)).strip()

    # €/kg pakken (probeer form-match eerst, anders zonder form)
    eurkg = None
    if not df_prices.empty:
        # Eerste poging: form uit BOM (bar/sheet)
        eurkg = latest_material_price(df_prices, grade=grade, region="EU", unit="€/kg")
        # NB: df kan meerdere vormen bevatten; jouw price loader kan je verder verfijnen op 'form' indien gewenst.

    m_kg = mass_kg(p)
    mat_eur_pc = (eurkg or 0.0) * m_kg

    # processen
    procs = [x.strip() for x in (p.get("processes") or [])]
    proc_cost_eur_per_pc = 0.0
    det = []
    for proc in procs:
        # normaliseer TIG hoofdletters
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
        "eur_per_kg": round((eurkg or 0.0), 4),
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
    st.warning("Geen €/kg gevonden voor: " + ", ".join(sorted(set(missing_prices))) + ". "
               "Zorg dat `material_prices.csv` deze grades bevat met `region='EU'` en `unit='€/kg'`.")

# ---------- Download
st.download_button(
    "⬇️ Download resultaten (CSV)",
    df_display.to_csv(index=False),
    file_name="routing_kosten_resultaten.csv",
    mime="text/csv"
)
