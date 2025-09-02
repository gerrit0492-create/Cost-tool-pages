import json, os
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Routing & Kosten", page_icon="🛠️", layout="wide")
st.title("🛠️ Routing & Kosten (v1)")

# -------- Helpers
DENSITY_KG_PER_MM3 = {
    "stainless": 7.9e-6,
    "duplex":    7.8e-6,
    "aluminum":  2.7e-6,
    "carbon_steel": 7.85e-6,
}

def latest_material_price(df_prices, grade, region="EU", unit="€/kg"):
    if df_prices.empty: 
        return None
    d = df_prices.copy()
    # zachte filters (grade verplicht, regio/unit optioneel)
    d = d[d["grade"].str.lower() == str(grade).lower()]
    if region:
        d = d[d["region"].str.upper() == str(region).upper()]
    if unit:
        d = d[d["unit"] == unit]
    if d.empty:
        return None
    d["as_of_date"] = pd.to_datetime(d["as_of_date"], errors="coerce")
    d = d.sort_values("as_of_date")
    return float(d.iloc[-1]["price"])

def midpoint_rate(df_rates, process, country="Netherlands"):
    if df_rates.empty:
        return None
    d = df_rates.copy()
    d = d[d["process"].str.lower().str.contains(process.lower())]
    if not d.empty and country:
        d2 = d[d["country"].str.lower() == country.lower()]
        if not d2.empty: d = d2
    if d.empty:
        return None
    d = d.sort_values("as_of_date")
    row = d.iloc[-1]
    return float((row["rate_min"] + row["rate_max"]) / 2.0) / 60.0  # €/min

def est_process_minutes(part, process):
    """Eenvoudige vuistregels per stuk + setup/qty."""
    q = max(1, int(part.get("qty", 1)))
    if process == "laser":
        setup = 5.0; cycle = 0.43
    elif process == "bend":
        setup = 8.0; cycle = 0.50
    elif process == "TIG":
        setup = 10.0; cycle = 0.60
    elif process == "CNC_mill":
        setup = 12.0; cycle = 1.20
    elif process == "CNC_turn":
        setup = 10.0; cycle = 1.00
    else:
        setup = 5.0;  cycle = 0.30
    return (setup / q) + cycle

def mass_kg(part):
    fam = (part.get("material_family") or "").lower()
    rho = DENSITY_KG_PER_MM3.get(fam, 7.85e-6)
    form = (part.get("form") or "").lower()
    t = part.get("thickness_mm") or 0
    L = part.get("length_mm") or 0
    W = part.get("width_mm") or 0
    dia = part.get("diameter_mm") or 0
    if form in ("sheet", "plate"):
        vol = float(t) * float(L) * float(W)              # mm^3
    elif form in ("bar","staf","round","rod") and dia and L:
        import math
        vol = math.pi * (float(dia)/2)**2 * float(L)     # mm^3
    else:
        # fallback kleine prisma
        vol = float(t) * float(L) * float(W)
    if vol <= 0: 
        return 0.0
    return vol * rho  # kg

# -------- Load data
if not os.path.exists("data/bom_current.json"):
    st.warning("Geen BOM gevonden. Ga eerst naar je BOM import pagina.")
    st.stop()

bom = json.load(open("data/bom_current.json")).get("bom", [])
df_prices = pd.read_csv("data/material_prices.csv") if os.path.exists("data/material_prices.csv") else pd.DataFrame()
df_rates  = pd.read_csv("data/labor_rates.csv") if os.path.exists("data/labor_rates.csv") else pd.DataFrame()

# -------- Calculate
rows = []
for p in bom:
    item = p.get("item_code","?")
    qty  = int(p.get("qty",1))
    grade = p.get("material_grade","").strip()
    fam   = p.get("material_family","").strip()

    # materiaal
    price_eur_per_kg = latest_material_price(df_prices, grade=grade, region="EU", unit="€/kg") or 0.0
    m_kg = mass_kg(p)
    mat_eur_per_pc = m_kg * price_eur_per_kg

    # processen
    procs = [x.strip() for x in (p.get("processes") or [])]
    proc_cost_eur_per_pc = 0.0
    proc_detail = []
    for proc in procs:
        # map vrij: 'bend','laser','TIG','CNC_mill','CNC_turn'
        rate_eur_min = None
        if proc.lower() == "laser":
            rate_eur_min = midpoint_rate(df_rates, "CNC milling") or 1.20  # fallback
        elif proc.lower() == "bend":
            rate_eur_min = midpoint_rate(df_rates, "CNC milling") or 1.10
        elif proc.upper() == "TIG":
            rate_eur_min = midpoint_rate(df_rates, "TIG") or 1.00
        elif proc.lower() == "cnc_mill":
            rate_eur_min = midpoint_rate(df_rates, "CNC milling") or 1.20
        elif proc.lower() == "cnc_turn":
            rate_eur_min = midpoint_rate(df_rates, "CNC") or 1.20
        else:
            rate_eur_min = midpoint_rate(df_rates, proc) or 1.00

        minutes = est_process_minutes(p, proc if proc != "TIG" else "TIG")
        cost_pc = minutes * rate_eur_min
        proc_cost_eur_per_pc += cost_pc
        proc_detail.append(f"{proc}@{rate_eur_min:.2f}€/min → {minutes:.2f} min")

    total_per_pc = mat_eur_per_pc + proc_cost_eur_per_pc

    rows.append({
        "item_code": item,
        "qty": qty,
        "material_family": fam,
        "grade": grade,
        "mass_kg_per_pc": round(m_kg, 4),
        "€/kg (latest)": round(price_eur_per_kg, 4),
        "Material €/pc": round(mat_eur_per_pc, 2),
        "Proc €/pc": round(proc_cost_eur_per_pc, 2),
        "Total €/pc": round(total_per_pc, 2),
        "Processes": " | ".join(proc_detail)
    })

df = pd.DataFrame(rows)
st.subheader("Per item")
st.dataframe(df, use_container_width=True)

st.subheader("Samenvatting")
sum_qty_value = (df["Total €/pc"] * pd.Series([r["qty"] for r in rows])).sum()
col1, col2, col3 = st.columns(3)
with col1: st.metric("Totaal items", len(df))
with col2: st.metric("Som Material €/pc", f"€ {df['Material €/pc'].sum():,.2f}")
with col3: st.metric("Som Proc €/pc", f"€ {df['Proc €/pc'].sum():,.2f}")
st.success(f"🌟 Totale waarde (qty * Total €/pc): € {sum_qty_value:,.2f}")

st.caption("Vuistregels v1: laser 0.43 min, bend 0.50 min, TIG 0.60 min + setup/qty. Tarieven = midden van je labor_rates (€/min). Materiaal = massa × €/kg (laatste prijs).")
