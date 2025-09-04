# pages/01_Calculatie.py

# Deze page rekent een eenvoudige kostprijs per regel in de BOM
# en toont een samenvatting. ImportErrors of ontbrekende CSV's
# worden netjes getoond i.p.v. een harde crash.

from __future__ import annotations
import streamlit as st
import pandas as pd

# Probeer de optionele opmaak/init van jouw app te gebruiken
try:
    from bootstrap import configure_page, init_state
except Exception:
    def configure_page():
        st.set_page_config(page_title="Calculatie", layout="wide")
    def init_state():
        pass

# Juiste imports: schema's + IO komen uit utils.io
from utils.io import (
    SCHEMA_MATERIALS,
    SCHEMA_PROCESSES,
    SCHEMA_BOM,
    read_csv_safe,
    paths,
)

# Kostrekenregels
try:
    from utils.costing import part_cost
except Exception:
    # Fallback voor wanneer costing (nog) niet aanwezig is
    def part_cost(material_kg, price_eur_per_kg, process_time_h, machine_rate_eur_h, labor_time_h, labor_rate_eur_h):
        return (material_kg or 0.0) * (price_eur_per_kg or 0.0) + \
               (process_time_h or 0.0) * (machine_rate_eur_h or 0.0) + \
               (labor_time_h or 0.0) * (labor_rate_eur_h or 0.0)

def guard(fn):
    """Zorg dat fouten netjes zichtbaar zijn en de page stopt."""
    try:
        fn()
    except Exception as e:
        st.error(f"Deze page kon niet starten: {type(e).__name__}: {e}")
        st.stop()

def main():
    configure_page()
    init_state()
    st.title("📐 Calculatie")

    P = paths()

    # Data inladen met schema-validatie
    materials = read_csv_safe(P["materials"], SCHEMA_MATERIALS)
    processes = read_csv_safe(P["processes"], SCHEMA_PROCESSES)
    bom = read_csv_safe(P["bom"], SCHEMA_BOM) if P["bom"].exists() else None

    # UI: hulp / status
    with st.expander("📁 Databestanden"):
        st.write(f"**Materials**: `{P['materials']}`")
        st.write(f"**Processes**: `{P['processes']}`")
        st.write(f"**BOM**: `{P['bom']}` (template mag ook)")

    if materials is None:
        st.error("Kon **materials** niet laden. Controleer `data/materials_db.csv`.")
        st.stop()

    # BOM upload of template
    up = st.file_uploader("Upload BOM CSV (of gebruik `data/bom_template.csv`)", type=["csv"])
    if up is not None:
        bom = pd.read_csv(up)

    if bom is None:
        st.warning("Geen BOM beschikbaar. Upload een CSV of plaats `data/bom_template.csv`.")
        st.stop()

    required = ["material_id", "qty", "mass_kg", "process_route"]
    missing = [c for c in required if c not in bom.columns]
    if missing:
        st.error(f"Ontbrekende BOM kolommen: {', '.join(missing)}")
        st.stop()

    # Merge materiaalprijzen
    view = bom.merge(
        materials[["material_id", "price_eur_per_kg"]],
        on="material_id",
        how="left"
    )

    st.sidebar.header("Aannames")
    lt_per_qty = st.sidebar.number_input("Arbeidstijd per stuk (uur)", min_value=0.0, value=0.10, step=0.05)
    mt_per_qty = st.sidebar.number_input("Machinetijd per stuk (uur)", min_value=0.0, value=0.05, step=0.05)
    labor_rate = st.sidebar.number_input("Arbeidsrate (€/h)", min_value=0.0, value=45.0, step=5.0)
    machine_rate = st.sidebar.number_input("Machinerate (€/h)", min_value=0.0, value=80.0, step=5.0)

    def calc_row(r: pd.Series) -> float:
        qty = float(r.get("qty") or 0.0)
        mk = float(r.get("mass_kg") or 0.0)
        price = float(r.get("price_eur_per_kg") or 0.0)
        lt = qty * lt_per_qty
        mt = qty * mt_per_qty
        return part_cost(mk, price, mt, machine_rate, lt, labor_rate)

    view["part_cost_eur"] = view.apply(calc_row, axis=1)
    total = float(view["part_cost_eur"].sum())

    # NL notatie zonder locale-gedoe
    def eur(x: float) -> str:
        return f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    st.metric("Totale kostprijs (demo)", eur(total))
    st.dataframe(view, use_container_width=True)

    # Optioneel: processen tonen als ze bestaan
    if processes is not None and not processes.empty:
        with st.expander("⚙️ Processen (tarieven)"):
            cols = [c for c in ["process_id", "machine_rate_eur_h", "labor_rate_eur_h", "overhead_pct", "margin_pct"] if c in processes.columns]
            st.dataframe(processes[cols], use_container_width=True)

guard(main)
