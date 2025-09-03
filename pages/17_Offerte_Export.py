from bootstrap import configure_page, init_state
configure_page(); init_state()

from utils.safe import run_safely
import os, json, pandas as pd, streamlit as st
from jinja2 import Environment, FileSystemLoader
from datetime import date

st.set_page_config(page_title="Offerte export", page_icon="📄", layout="wide")
st.title("📄 Offerte export (Markdown)")

# --- Input velden voor koptekst
col1, col2 = st.columns(2)
client_name   = col1.text_input("Klantnaam", "Acme BV")
client_contact= col1.text_input("Contact", "J. Janssen")
client_email  = col1.text_input("Email", "sales@acme.nl")
project_code  = col2.text_input("Projectcode", "RFQ-2025-001")
lead_weeks    = col2.number_input("Levertijd (weken)", 1, 52, 4)

# --- Data inladen
missing = []
if not os.path.exists("data/bom_current.json"):
    missing.append("data/bom_current.json (BOM)")
if not os.path.exists("data/material_prices.csv"):
    missing.append("data/material_prices.csv (materiaalprijzen)")
if not os.path.exists("data/labor_rates.csv"):
    missing.append("data/labor_rates.csv (uurtarieven)")

if missing:
    st.error("Ontbrekend voor offerte:\n- " + "\n- ".join(missing))
    st.stop()

bom = json.load(open("data/bom_current.json"))
bom_items = bom.get("bom", [])
assembly = bom.get("assembly", {"name":"", "qty":1})

df_prices = run_safely("read_csv", pd.read_csv, "data/material_prices.csv")
df_rates  = run_safely("read_csv", pd.read_csv, "data/labor_rates.csv")

# --- Kleine helpers (zelfde logica als Routing v1)
DENSITY_KG_PER_MM3 = {
    "stainless": 7.9e-6, "duplex": 7.8e-6, "aluminum": 2.7e-6, "carbon_steel": 7.85e-6
}
def infer_family_from_grade(grade:str)->str:
    g = (grade or "").lower()
    if "1.44" in g or "2205" in g or "s31803" in g or "s32205" in g: return "duplex"
    if any(k in g for k in ["304","316","1.43","1.45"]): return "stainless"
    if any(k in g for k in ["6082","6061","5754","1050","alu","aluminium"]): return "aluminum"
    return "carbon_steel"

def mass_kg(part):
    fam = (part.get("material_family") or infer_family_from_grade(part.get("material_grade",""))).lower()
    rho = DENSITY_KG_PER_MM3.get(fam, 7.85e-6)
    form = (part.get("form") or "").lower()
    t = part.get("thickness_mm") or 0; L = part.get("length_mm") or 0
    W = part.get("width_mm") or 0; dia = part.get("diameter_mm") or 0
    if form in ("sheet","plate"):
        vol = float(t)*float(L)*float(W)
    elif form in ("bar","staf","round","rod") and dia and L:
        import math; vol = math.pi*(float(dia)/2)**2*float(L)
    else:
        vol = float(t)*float(L)*float(W)
    return max(0.0, vol) * rho

def latest_material_price(df, grade, region="EU", unit="€/kg"):
    d = df.copy()
    d = d[d["grade"].astype(str).str.lower() == str(grade).lower()]
    if region: d = d[d["region"].astype(str).str.upper() == str(region).upper()]
    if unit:   d = d[d["unit"].astype(str) == unit]
    if d.empty: return 0.0
    d["as_of_date"] = pd.to_datetime(d["as_of_date"], errors="coerce")
    d = d.sort_values("as_of_date")
    return float(d.iloc[-1]["price"])

def midpoint_rate(df, process, country="Netherlands"):
    d = df.copy()
    d = d[d["process"].astype(str).str.lower().str.contains(process.lower())]
    if not d.empty:
        d2 = d[d["country"].astype(str).str.lower() == country.lower()]
        if not d2.empty: d = d2
    if d.empty: return 1.00/60.0
    d = d.sort_values("as_of_date")
    r = d.iloc[-1]
    return float((r["rate_min"] + r["rate_max"]) / 2.0) / 60.0

def est_minutes(part, proc):
    q = max(1, int(part.get("qty",1)))
    base = {"laser":(5,0.43),"bend":(8,0.50),"TIG":(10,0.60),"CNC_mill":(12,1.20),"CNC_turn":(10,1.00)}
    setup, cycle = base.get(proc, (5,0.30))
    return (setup/q) + cycle

# --- Reken per item
rows=[]
for p in bom_items:
    grade = p.get("material_grade","")
    fam = p.get("material_family") or infer_family_from_grade(grade)
    m_kg = mass_kg(p)
    eur_per_kg = latest_material_price(df_prices, grade)
    mat_eur_pc = m_kg * eur_per_kg

    procs = [x.strip() for x in (p.get("processes") or [])]
    proc_detail = []
    proc_cost_pc = 0.0
    for proc in procs:
        if proc.lower()=="laser": rate = midpoint_rate(df_rates,"CNC milling")
        elif proc.lower()=="bend": rate = midpoint_rate(df_rates,"CNC milling")
        elif proc.upper()=="TIG": rate = midpoint_rate(df_rates,"TIG")
        elif proc.lower()=="cnc_mill": rate = midpoint_rate(df_rates,"CNC milling")
        elif proc.lower()=="cnc_turn": rate = midpoint_rate(df_rates,"CNC")
        else: rate = midpoint_rate(df_rates,proc)
        minutes = est_minutes(p, "TIG" if proc=="TIG" else proc)
        cost_pc = minutes * rate
        proc_cost_pc += cost_pc
        proc_detail.append({"proc":proc, "rate_eur_min": round(rate,2), "minutes": round(minutes,2), "cost_eur": round(cost_pc,2)})

    total_pc = mat_eur_pc + proc_cost_pc

    rows.append({
        "item_code": p.get("item_code","?"),
        "qty": int(p.get("qty",1)),
        "grade": grade,
        "family": fam,
        "mass_kg_per_pc": round(m_kg,4),
        "eur_per_kg": round(eur_per_kg,4),
        "material_eur_pc": round(mat_eur_pc,2),
        "proc_eur_pc": round(proc_cost_pc,2),
        "total_eur_pc": round(total_pc,2),
        "proc_detail": proc_detail
    })

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True)

# --- Totals
total_value = (df["total_eur_pc"] * df["qty"]).sum()
st.success(f"Totale waarde (qty * Total €/pc): € {total_value:,.2f}")

# --- Render Markdown via Jinja2
env = Environment(loader=FileSystemLoader("templates"))
tpl_name = "offerte_v1.md.j2"
if not os.path.exists(os.path.join("templates", tpl_name)):
    st.error(f"Template ontbreekt: templates/{tpl_name}")
    st.stop()

context = {
    "project": {"code": project_code, "date": str(date.today())},
    "client":  {"name": client_name, "contact": client_contact, "email": client_email},
    "assembly":{"name": assembly.get("name",""), "qty": assembly.get("qty",1)},
    "items": rows,
    "totals": {"total_value": round(total_value,2)},
    "assumptions": {
        "lead_time_weeks": int(lead_weeks),
        "incoterms": "EXW",
        "weld_quality": "C",
        "scrap_pct": "3%"
    }
}
md = env.get_template(tpl_name).render(**context)

st.download_button("⬇️ Download offerte.md", md, file_name=f"offerte_{project_code}.md", mime="text/markdown")
st.caption("Je kunt dit markdown-bestand direct openen in VS Code, Notion of converteren naar PDF.")
