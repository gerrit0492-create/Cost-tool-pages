from bootstrap import configure_page, init_state
configure_page(); init_state()

from utils.safe import run_safely
# pages/01_Calculatie.py

import traceback
import streamlit as st
from pathlib import Path

# Altijd EERST page_config vóór enig ander Streamlit UI-commando
st.set_page_config(page_title="Calculatie", page_icon="🧮", layout="wide")

# --- optioneel: bootstrap zodat repo-root op sys.path staat ---
try:
    from bootstrap import ROOT  # uit je repo-root
except Exception:
    ROOT = Path(__file__).resolve().parent.parent  # fallback

def guard(run):
    try:
        run()
    except Exception:
        err = traceback.format_exc()
        st.exception(err)
        st.session_state["last_exception"] = err

def main():
    st.title("🔧 Calculatie")

    # === Debug-schakelaar (standaard UIT) ===
    qp = st.query_params
    DEBUG = ("debug" in qp and qp["debug"] in ("1", "true", "True")) or bool(st.secrets.get("DEBUG", False))

    if DEBUG:
        import sys
        st.subheader("🔧 Debug")
        st.code(f"sys.path[0:3] →\n{sys.path[0:3]!r}")
        st.code("root files →\n" + str(sorted([p.name for p in ROOT.iterdir()])))
        utils_dir = ROOT / "utils"
        if utils_dir.exists():
            st.code("utils files →\n" + str(sorted([p.name for p in utils_dir.iterdir()])))

    # ===== App imports (na eventuele sys.path fix) =====
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    from utils.shared import (
        MATERIALS, ROUTING_COLS, BOM_COLS, LABOR, MACHINE_RATES,
        fetch_otk, OTK_KEY, eurton, fetch_lme_eur_ton,
        cost_once, run_mc, capacity_table
    )

    # ===== Invoer =====
    c0, c1, c2, c3 = st.columns(4)
    with c0:
        project = st.text_input("Project", st.session_state.get("project", "Demo"))
    with c1:
        Q = st.number_input("Aantal stuks (Q)", 1, 100000, st.session_state.get("Q", 50))
    with c2:
        mat_keys = list(MATERIALS.keys())
        default_mat = st.session_state.get("mat", "1.4462_Duplex")
        mat_index = mat_keys.index(default_mat) if default_mat in mat_keys else 0
        mat = st.selectbox("Materiaal", mat_keys, index=mat_index)
    with c3:
        netkg = st.number_input("Netto kg/stuk", 0.01, 10000.0, st.session_state.get("netkg", 2.0))

    # ===== Materiaalprijs =====
    kind = MATERIALS[mat]["kind"]
    src = "fixed"
    price = MATERIALS[mat]["base_eurkg"]

    with st.expander("Materiaalprijs", expanded=True):
        if kind == "stainless":
            mode = st.radio("Outokumpu bron", ["Auto", "Manual"], horizontal=True)
            manual_otk = st.number_input("OTK (€/ton)", 0.0, 100000.0, 0.0, 10.0)
            if mode == "Auto":
                data = fetch_otk()
                sur = eurton(data.get(OTK_KEY.get(mat, ""), 0.0))
                src = "OTK scraped"
            else:
                sur = eurton(manual_otk)
                src = "OTK manual"
            price = MATERIALS[mat]["base_eurkg"] + sur

        elif kind == "aluminium":
            lme_mode = st.radio("LME bron", ["Auto", "Manual"], horizontal=True)
            manual_lme = st.number_input("LME (€/ton)", 0.0, 100000.0, 2200.0, 10.0)
            prem = st.number_input("Regiopremie (€/kg)", 0.0, 10.0, 0.25, 0.01)
            conv_add = st.number_input("Conversie-opslag (€/kg)", 0.0, 10.0, 0.40, 0.01)
            if lme_mode == "Auto":
                lme, s = fetch_lme_eur_ton()
                if lme is None:
                    lme, s = manual_lme, "LME manual"
            else:
                lme, s = manual_lme, "LME manual"
            price = eurton(lme) + prem + conv_add
            src = f"{s} + prem+conv"

    st.success(f"Actuele prijs: € {price:.3f}/kg  •  {src}")

    # ===== Lean/energie/transport =====
    with st.expander("Lean / Energie / Transport"):
        energy = st.number_input("Energie (€/kWh)", 0.0, 2.0, st.session_state.get("energy", 0.20), 0.01)
        storage_days = st.number_input("Opslagdagen", 0.0, 365.0, st.session_state.get("storage_days", 0.0), 0.5)
        storage_cost = st.number_input("Opslagkosten (€/dag/batch)", 0.0, 2000.0, st.session_state.get("storage_cost", 0.0), 0.5)
        km = st.number_input("Transport (km)", 0.0, 100000.0, st.session_state.get("km", 0.0), 1.0)
        eur_km = st.number_input("Tarief (€/km)", 0.0, 50.0, st.session_state.get("eur_km", 0.0), 0.1)
        rework = st.number_input("Herbewerkingskans (%)", 0.0, 100.0, st.session_state.get("rework", 0.0), 0.5) / 100.0
        rework_min = st.number_input("Herbewerkingsminuten/stuk", 0.0, 240.0, st.session_state.get("rework_min", 0.0), 1.0)

    # ===== Routing/BOM =====
    if "routing_df" not in st.session_state:
        st.session_state["routing_df"] = pd.DataFrame(
            [{
                "Step": 10, "Proces": "CNC", "Qty_per_parent": 1.0, "Cycle_min": 6.0, "Setup_min": 20.0,
                "Attend_pct": 100, "kWh_pc": 0.18, "QA_min_pc": 0.5, "Scrap_pct": 0.02,
                "Parallel_machines": 1, "Batch_size": 50, "Queue_days": 0.5
            }],
            columns=ROUTING_COLS
        )
    if "bom_df" not in st.session_state:
        st.session_state["bom_df"] = pd.DataFrame(
            [{"Part": "Voorbeeld", "Qty": 1, "UnitPrice": 1.50, "Scrap_pct": 0.01}],
            columns=BOM_COLS
        )

    st.subheader("Routing")
    st.session_state["routing_df"] = pd.DataFrame(
        st.data_editor(st.session_state["routing_df"], num_rows="dynamic", use_container_width=True)
    )

    st.subheader("BOM / Inkoop")
    st.session_state["bom_df"] = pd.DataFrame(
        st.data_editor(st.session_state["bom_df"], num_rows="dynamic", use_container_width=True)
    )

    # ===== Berekening =====
    res = cost_once(
        st.session_state["routing_df"], st.session_state["bom_df"], Q, netkg, price,
        energy, LABOR, MACHINE_RATES, storage_days, storage_cost, km, eur_km, rework, rework_min
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Materiaal €/stuk", f"€ {res['mat_pc']:.2f}")
    c2.metric("Conversie", f"€ {res['conv_total']:.2f}")
    c3.metric("Lean", f"€ {res['lean_total']:.2f}")
    c4.metric("Inkoop", f"€ {res['buy_total']:.2f}")
    c5.metric("Kostprijs/stuk", f"€ {res['total_pc']:.2f}")

    st.plotly_chart(
        go.Figure(go.Pie(labels=["Materiaal", "Conversie", "Lean", "Inkoop"],
                         values=[res['mat_pc'], res['conv_total'], res['lean_total'], res['buy_total']])),
        use_container_width=True
    )

    # ===== Monte-Carlo =====
    with st.expander("Monte-Carlo"):
        mc_on = st.checkbox("Aanzetten", False)
        iters = st.number_input("Iteraties", 100, 20000, 1000, 100)
        sd_mat = st.number_input("σ materiaal (%)", 0.0, 0.5, 0.05, 0.01)
        sd_cycle = st.number_input("σ cyclustijd (%)", 0.0, 0.5, 0.08, 0.01)
        sd_scrap = st.number_input("σ scrap (additief)", 0.0, 0.5, 0.01, 0.005)
        mc_samples = None
        if mc_on:
            mc_samples = run_mc(
                st.session_state["routing_df"], st.session_state["bom_df"], Q, netkg, price,
                sd_mat, sd_cycle, sd_scrap, iters,
                energy=energy, labor=LABOR, mrates=MACHINE_RATES,
                storage_days=storage_days, storage_cost=storage_cost,
                km=km, eur_km=eur_km, rework=rework, rework_min=rework_min
            )
            st.plotly_chart(px.histogram(pd.DataFrame({"UnitCost": mc_samples}), x="UnitCost", nbins=40),
                            use_container_width=True)

    # ===== Capaciteit =====
    st.subheader("Capaciteit")
    hours_day = st.number_input("Uren productie per dag", 1.0, 24.0, 8.0, 0.5)
    with st.expander("Capaciteit per proces (h/dag)"):
        cap_proc = {p: st.number_input(f"{p}", 0.0, 24.0, 8.0, key=f"cap_{p}") for p in MACHINE_RATES}
    cap_df = capacity_table(st.session_state["routing_df"], Q, hours_day, cap_proc)
    if not cap_df.empty:
        show = cap_df.copy()
        show["Util_%"] = (show["Util_pct"] * 100).round(1)
        st.dataframe(show, use_container_width=True)

    # ===== Session doorgeven aan Rapport =====
    st.session_state.update({
        "project": project, "Q": Q, "mat": mat, "netkg": netkg,
        "price": price, "price_src": src, "res": res,
        "mc_samples": mc_samples, "cap_df": cap_df
    })

guard(main)
