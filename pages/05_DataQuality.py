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
# pages/05_DataQuality.py
import os, sys, io
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# Optioneel: shared-functies (alleen nodig voor capaciteit / context)
try:
    from utils.shared import ROUTING_COLS, BOM_COLS, capacity_table, MACHINE_RATES
except Exception:
    ROUTING_COLS = ["Step","Proces","Qty_per_parent","Cycle_min","Setup_min","Attend_pct","kWh_pc","QA_min_pc","Scrap_pct","Parallel_machines","Batch_size","Queue_days"]
    BOM_COLS     = ["Part","Qty","UnitPrice","Scrap_pct"]
    MACHINE_RATES= {"CNC":85.0,"Laser":110.0,"Lassen":55.0,"Buigen":75.0,"Montage":40.0,"Casting":65.0}
    capacity_table = None  # fallback

st.set_page_config(page_title="Data Quality / Audit", page_icon="🧪", layout="wide")
st.title("🧪 Data Quality / Audit")

st.caption("Controleert Routing en BOM op typische fouten, geeft suggesties en kan (veilig) auto-fixes toepassen. Exporteer het auditlog als CSV.")

# --- Haal input uit session ---
routing = st.session_state.get("routing_df")
bom     = st.session_state.get("bom_df")
Q       = st.session_state.get("Q", 1)
project = st.session_state.get("project", "Project")
mat     = st.session_state.get("mat", "")
price   = st.session_state.get("price", None)

if routing is None or bom is None:
    st.warning("Ga eerst naar **01_Calculatie** om Routing en BOM te vullen.")
    st.stop()

routing = pd.DataFrame(routing).copy()
bom     = pd.DataFrame(bom).copy()

# ---------- Auditregels ----------
def audit_routing(df: pd.DataFrame) -> pd.DataFrame:
    issues = []
    req = set(ROUTING_COLS)
    missing_cols = [c for c in ROUTING_COLS if c not in df.columns]
    if missing_cols:
        issues.append(("Routing","SCHEMA","HIGH","Ontbrekende kolommen", ", ".join(missing_cols), "Voeg kolommen toe of importeer juiste template.", None))

    # Alleen verder checken op bestaande kolommen
    def g(col, default=None):
        return df[col] if col in df.columns else pd.Series([default]*len(df), index=df.index)

    # 1) Stap-duplicaten / sortering
    if "Step" in df.columns:
        if df["Step"].duplicated().any():
            dup = sorted(df.loc[df["Step"].duplicated(),"Step"].unique().tolist())
            issues.append(("Routing","DUP_STEP","MED","Dubbele Step-waarden", str(dup), "Maak steps uniek of sorteer/renummer.", "auto_sort"))
        if not df["Step"].is_monotonic_increasing:
            issues.append(("Routing","ORDER","LOW","Step niet oplopend", "", "Sorteer op Step.", "auto_sort"))
    else:
        issues.append(("Routing","NO_STEP","HIGH","Step kolom ontbreekt","", "Voeg 'Step' toe.", None))

    # 2) Negatieve of onmogelijke tijden/waarden
    for col in ["Cycle_min","Setup_min","QA_min_pc","kWh_pc","Queue_days"]:
        if col in df.columns and (df[col].fillna(0) < 0).any():
            issues.append(("Routing","NEG", "HIGH", f"Negatieve waarden in {col}", "", f"Zet {col} minimaal op 0.", f"floor0:{col}"))

    # 3) Attend_pct buiten 0–100
    if "Attend_pct" in df.columns:
        bad = df["Attend_pct"].dropna()
        if ((bad < 0) | (bad > 100)).any():
            issues.append(("Routing","ATTEND", "MED", "Attend_pct buiten 0–100", "", "Klem tussen 0 en 100.", "clip_attend"))

    # 4) Scrap_pct buiten 0–0.35
    if "Scrap_pct" in df.columns:
        bad = df["Scrap_pct"].fillna(0)
        if ((bad < 0) | (bad > 0.35)).any():
            issues.append(("Routing","SCRAP", "MED", "Scrap_pct buiten 0–0.35", "", "Klem tussen 0 en 0.35.", "clip_scrap"))

    # 5) Parallel_machines < 1, Batch_size < 1, Qty_per_parent <= 0
    for col, label in [("Parallel_machines","Parallel_machines"),("Batch_size","Batch_size")]:
        if col in df.columns and (df[col].fillna(0) < 1).any():
            issues.append(("Routing","MIN1","HIGH", f"{label} < 1", "", f"Zet {label} minimaal op 1.", f"min1:{col}"))
    if "Qty_per_parent" in df.columns and (df["Qty_per_parent"].fillna(0) <= 0).any():
        issues.append(("Routing","QTY", "HIGH", "Qty_per_parent ≤ 0", "", "Zet minimaal op 0.001.", "min_qty"))

    # 6) Onbekende processen (zonder tarief)
    if "Proces" in df.columns:
        unknown = sorted(set(df["Proces"].dropna().astype(str)) - set(MACHINE_RATES.keys()))
        if unknown:
            issues.append(("Routing","PROC","LOW", "Onbekende processen", ", ".join(unknown), "Voeg machine rate toe in stamdata of hernoem proces.", None))

    # 7) Lege regels
    empty_rows = df.index[df.isna().all(axis=1)].tolist()
    if empty_rows:
        issues.append(("Routing","EMPTY", "LOW", f"Lege rijen ({len(empty_rows)})", str(empty_rows[:5]) + ("..." if len(empty_rows)>5 else ""), "Verwijder lege rijen.", "drop_empty"))

    return pd.DataFrame(issues, columns=["Table","Rule","Severity","Issue","Details","Suggestion","AutoFix"])

def audit_bom(df: pd.DataFrame) -> pd.DataFrame:
    issues = []
    missing_cols = [c for c in BOM_COLS if c not in df.columns]
    if missing_cols:
        issues.append(("BOM","SCHEMA","HIGH","Ontbrekende kolommen", ", ".join(missing_cols), "Voeg kolommen toe of importeer juiste template.", None))

    if "Qty" in df.columns and (df["Qty"].fillna(0) <= 0).any():
        issues.append(("BOM","QTY","HIGH","Qty ≤ 0", "", "Zet minimaal op 0.001.", "min_qty"))
    if "UnitPrice" in df.columns:
        if df["UnitPrice"].isna().any():
            issues.append(("BOM","PRICE_NA","MED","Ontbrekende UnitPrice", "", "Vul prijs in.", None))
        if (df["UnitPrice"].fillna(0) < 0).any():
            issues.append(("BOM","PRICE_NEG","HIGH","UnitPrice negatief", "", "Zet minimaal op 0.", "floor0:UnitPrice"))
    if "Scrap_pct" in df.columns and ((df["Scrap_pct"].fillna(0) < 0) | (df["Scrap_pct"].fillna(0) > 0.35)).any():
        issues.append(("BOM","SCRAP","MED","Scrap_pct buiten 0–0.35", "", "Klem tussen 0 en 0.35.", "clip_scrap"))
    if df.isna().all(axis=1).any():
        idx = df.index[df.isna().all(axis=1)].tolist()
        issues.append(("BOM","EMPTY","LOW",f"Lege rijen ({len(idx)})", str(idx[:5])+("..." if len(idx)>5 else ""), "Verwijder lege rijen.", "drop_empty"))
    return pd.DataFrame(issues, columns=["Table","Rule","Severity","Issue","Details","Suggestion","AutoFix"])

def audit_context() -> pd.DataFrame:
    issues=[]
    # Materiaalprijs 0 bij aluminium → waarschuwing
    if mat and "Al" in str(mat) and (price is None or price <= 0):
        issues.append(("Context","MAT_PRICE","MED","Aluminiumprijs = 0", "", "Gebruik LME + premie + conversie of handmatige override.", None))
    # Q logisch?
    if Q <= 0:
        issues.append(("Context","Q","HIGH","Q ≤ 0","", "Zet Q minimaal op 1.", None))
    return pd.DataFrame(issues, columns=["Table","Rule","Severity","Issue","Details","Suggestion","AutoFix"])

# ---------- Uitvoeren ----------
routing_issues = audit_routing(routing)
bom_issues     = audit_bom(bom)
ctx_issues     = audit_context()
issues = pd.concat([routing_issues, bom_issues, ctx_issues], ignore_index=True)

# ---------- Overzicht ----------
st.subheader("Samenvatting")
if issues.empty:
    st.success("Geen problemen gevonden. Mooie data! ✅")
else:
    counts = (issues.groupby(["Table","Severity"]).size()
              .rename("Count").reset_index()
              .pivot(index="Table", columns="Severity", values="Count").fillna(0).astype(int))
    st.dataframe(counts, use_container_width=True)
    st.dataframe(issues, use_container_width=True)

    # Download audit CSV
    csv_bytes = issues.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download auditlog (CSV)", csv_bytes,
                       file_name=f"{project}_audit_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                       mime="text/csv")

st.markdown("---")

# ---------- Auto-fix acties ----------
st.subheader("Auto-fixes (veilig & omkeerbaar in deze sessie)")
st.caption("Kies welke automatische reparaties je wilt uitvoeren. Er wordt een kopie in de sessie weggeschreven; je oorspronkelijke data vervang je alleen als je op **Toepassen** klikt.")

fix_cols = st.columns(4)
do_sort      = fix_cols[0].checkbox("Sorteer & de-dup Step (Routing)", value=True)
do_clip_scr  = fix_cols[1].checkbox("Klem Scrap_pct 0–0.35 (Routing & BOM)", value=True)
do_clip_att  = fix_cols[2].checkbox("Klem Attend 0–100 (Routing)", value=True)
do_floor_min = fix_cols[3].checkbox("Minima: ≥0 of ≥1 (Routing & BOM)", value=True)

if st.button("Toepassen"):
    rout_fix = routing.copy()
    bom_fix  = bom.copy()

    # Routing fixes
    if do_sort and "Step" in rout_fix.columns:
        # de-dup door rangnummering en groep-sorting
        rout_fix = rout_fix.sort_values("Step").reset_index(drop=True)
        # Voeg achteraf unieke Step toe indien duplicaten
        if rout_fix["Step"].duplicated().any():
            # renummer oplopend per rij (10,20,30,…)
            rout_fix["Step"] = (np.arange(len(rout_fix))+1) * 10

    if do_clip_scr and "Scrap_pct" in rout_fix.columns:
        rout_fix["Scrap_pct"] = rout_fix["Scrap_pct"].fillna(0).clip(0.0, 0.35)

    if do_clip_att and "Attend_pct" in rout_fix.columns:
        rout_fix["Attend_pct"] = rout_fix["Attend_pct"].fillna(100).clip(0.0, 100.0)

    if do_floor_min:
        for col in ["Cycle_min","Setup_min","QA_min_pc","kWh_pc","Queue_days"]:
            if col in rout_fix.columns:
                rout_fix[col] = rout_fix[col].fillna(0).clip(lower=0.0)
        for col in ["Parallel_machines","Batch_size"]:
            if col in rout_fix.columns:
                rout_fix[col] = rout_fix[col].fillna(1).clip(lower=1)
        if "Qty_per_parent" in rout_fix.columns:
            rout_fix["Qty_per_parent"] = rout_fix["Qty_per_parent"].fillna(0.001).clip(lower=0.001)

    # BOM fixes
    if do_clip_scr and "Scrap_pct" in bom_fix.columns:
        bom_fix["Scrap_pct"] = bom_fix["Scrap_pct"].fillna(0).clip(0.0, 0.35)
    if do_floor_min:
        if "UnitPrice" in bom_fix.columns:
            bom_fix["UnitPrice"] = bom_fix["UnitPrice"].fillna(0).clip(lower=0.0)
        if "Qty" in bom_fix.columns:
            bom_fix["Qty"] = bom_fix["Qty"].fillna(0.001).clip(lower=0.001)

    st.session_state["routing_df_fixed"] = rout_fix
    st.session_state["bom_df_fixed"]     = bom_fix

    st.success("Auto-fixes toegepast op kopieën in deze sessie. Bekijk hieronder de resultaten en kies of je ze wilt overnemen.")

# Toon fixed-views (indien gemaakt)
if "routing_df_fixed" in st.session_state or "bom_df_fixed" in st.session_state:
    st.markdown("### Resultaat (na auto-fix)")
    if "routing_df_fixed" in st.session_state:
        st.write("**Routing (fixed)**")
        st.dataframe(st.session_state["routing_df_fixed"], use_container_width=True)
    if "bom_df_fixed" in st.session_state:
        st.write("**BOM (fixed)**")
        st.dataframe(st.session_state["bom_df_fixed"], use_container_width=True)

    col_apply1, col_apply2, col_dl = st.columns([1,1,2])
    if col_apply1.button("Vervang originele Routing door fixed"):
        st.session_state["routing_df"] = st.session_state["routing_df_fixed"].copy()
        st.success("Routing vervangen door fixed-versie.")
    if col_apply2.button("Vervang originele BOM door fixed"):
        st.session_state["bom_df"] = st.session_state["bom_df_fixed"].copy()
        st.success("BOM vervangen door fixed-versie.")

    # Download fixed CSV's
    if "routing_df_fixed" in st.session_state:
        col_dl.download_button("⬇️ Download Routing (fixed CSV)",
                               st.session_state["routing_df_fixed"].to_csv(index=False).encode("utf-8"),
                               file_name=f"{project}_Routing_fixed.csv",
                               mime="text/csv")
    if "bom_df_fixed" in st.session_state:
        col_dl.download_button("⬇️ Download BOM (fixed CSV)",
                               st.session_state["bom_df_fixed"].to_csv(index=False).encode("utf-8"),
                               file_name=f"{project}_BOM_fixed.csv",
                               mime="text/csv")

st.markdown("---")

# ---------- Extra: Capaciteit sanity (optioneel) ----------
st.subheader("Capaciteit sanity-check (optioneel)")
hours_day = st.number_input("Uren productie per dag", 1.0, 24.0, 8.0, 0.5)
cap_proc = {p: st.number_input(f"Capaciteit {p} (h/dag)", 0.0, 24.0, 8.0, key=f"audit_cap_{p}") for p in MACHINE_RATES}

if capacity_table is not None:
    cap_df = capacity_table(st.session_state.get("routing_df", routing), Q, hours_day, cap_proc)
    if not cap_df.empty:
        cap_df["Util_%"] = (cap_df["Util_pct"]*100).round(1)
        st.dataframe(cap_df, use_container_width=True)
        hard_over = cap_df[cap_df["Util_pct"]>1.0]
        if not hard_over.empty:
            st.warning(f"**Overbelast**: {', '.join(hard_over['Proces'].astype(str))} (>{100.0:.0f}% benutting). Overweeg extra parallelle machines, batchgroottes of cyclus/insteloptimalisatie.")
else:
    st.info("Capaciteitstabel niet beschikbaar (fallback). Dit vereist `utils.shared.capacity_table`.")
