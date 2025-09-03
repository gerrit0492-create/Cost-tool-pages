from bootstrap import configure_page, init_state
configure_page(); init_state()

from utils.safe import run_safely
import streamlit as st
import pandas as pd
import math

st.title("🧮 Routing & bewerkingstijd")

# Eenvoudige inputs (kun je later koppelen aan processes_db.csv)
c1, c2 = st.columns(2)
with c1:
    machine_rate = st.number_input("Machine rate €/h", value=95.0, step=1.0)
with c2:
    labor_rate = st.number_input("Labor rate €/h", value=45.0, step=1.0)

oh = st.slider("Overhead %", 0, 50, 25) / 100
m  = st.slider("Marge %", 0, 40, 10) / 100

def cost_setup_minutes(setup_min, mr, lr):  return (setup_min/60.0) * (mr + lr)
def cost_runtime_minutes(rt_min, mr, lr):   return (rt_min/60.0) * (mr + lr)
def cost_with_overheads(base, oh, m):       return base * (1 + oh) * (1 + m)

def cnc_mill_time(toolpath_mm, feed_mm_min, passes=1, retract_penalty_min=0.15, k_complexity=1.0):
    return (toolpath_mm / max(feed_mm_min, 1)) * k_complexity + passes * retract_penalty_min

def laser_time(cut_len_mm, cut_speed_mm_min, pierces, pierce_time_min=0.2):
    return (cut_len_mm / max(cut_speed_mm_min, 1)) + pierces * pierce_time_min

def bend_time(bends, rotate_penalty_min=0.1): return bends * (0.5 + rotate_penalty_min)
def weld_time(weld_len_mm, dep_rate_mm_min, k_precision=1.0): return (weld_len_mm / max(dep_rate_mm_min,1)) * k_precision

tab1, tab2 = st.tabs(["Laser + Buigen + Frezen", "Lassen + Frezen"])

def show_route(route):
    rows, total = [], 0.0
    for i, step in enumerate(route, start=1):
        setup = cost_setup_minutes(step.get("setup_min",0), machine_rate, labor_rate)
        runtime = cost_runtime_minutes(step.get("runtime_min",0), machine_rate, labor_rate)
        base = setup + runtime
        rows.append({"seq":i,"op":step.get("op"),
                     "setup_eur":round(setup,2),"runtime_eur":round(runtime,2),
                     "base_eur":round(base,2),"note":step.get("note","")})
        total += base
    df = pd.DataFrame(rows)
    final = cost_with_overheads(total, oh, m)
    st.dataframe(df, use_container_width=True)
    st.metric("Totaal (excl. OH & marge)", f"€ {total:,.2f}")
    st.metric("Eindprijs (incl. OH & marge)", f"€ {final:,.2f}")

with tab1:
    l = st.number_input("Laser snijlengte (mm)", 800.0, step=10.0)
    v = st.number_input("Laser snelheid (mm/min)", 2500.0, step=10.0)
    pierces = st.number_input("Aantal pierces", 6, step=1)
    bends = st.number_input("Aantal buigingen", 4, step=1)
    toolpath = st.number_input("Frezen toolpath (mm)", 1500.0, step=10.0)
    feed = st.number_input("Frezen voeding (mm/min)", 600.0, step=10.0)

    route = [
        {"op":"LASER","setup_min":10,"runtime_min": laser_time(l, v, pierces)},
        {"op":"BEND","setup_min":8,"runtime_min": bend_time(bends)},
        {"op":"CNC_MILL","setup_min":12,"runtime_min": cnc_mill_time(toolpath, feed, passes=2, k_complexity=1.1)},
    ]
    show_route(route)

with tab2:
    wl = st.number_input("Laslengte (mm)", 300.0, step=10.0)
    dep = st.number_input("Neersmelt (mm/min)", 80.0, step=1.0)
    tp = st.number_input("Frezen toolpath (mm)", 900.0, step=10.0)
    fd = st.number_input("Voeding (mm/min)", 500.0, step=10.0)

    route = [
        {"op":"WELD_TIG","setup_min":15,"runtime_min": weld_time(wl, dep, k_precision=1.2)},
        {"op":"CNC_MILL","setup_min":10,"runtime_min": cnc_mill_time(tp, fd, passes=1)},
    ]
    show_route(route)
