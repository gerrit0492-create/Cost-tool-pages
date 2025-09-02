# pages/98_🧪_Schema_Check.py
from __future__ import annotations
from pathlib import Path
import sys
import streamlit as st
import pandas as pd

st.set_page_config(page_title="🧪 Schema Check", page_icon="🧪", layout="wide")
st.title("🧪 Schema Check – routing_df & bom_df")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from utils.validators import (
        ROUTING_SCHEMA, BOM_SCHEMA, diff_schema, fix_schema
    )
except Exception as e:
    st.error("Kon utils.validators niet importeren.")
    st.exception(e)
    st.stop()

def _get_df(key: str, fallback_cols: list[str]) -> pd.DataFrame:
    df = st.session_state.get(key)
    if isinstance(df, pd.DataFrame):
        return df
    return pd.DataFrame(columns=fallback_cols)

# Huidige state
routing_df = _get_df("routing_df", ROUTING_SCHEMA.columns)
bom_df = _get_df("bom_df", BOM_SCHEMA.columns)

c1, c2 = st.columns(2)
with c1:
    st.subheader("routing_df – huidige")
    st.dataframe(routing_df, use_container_width=True)
with c2:
    st.subheader("bom_df – huidige")
    st.dataframe(bom_df, use_container_width=True)

st.divider()
st.subheader("Analyse")

rd = diff_schema(routing_df, ROUTING_SCHEMA)
bd = diff_schema(bom_df, BOM_SCHEMA)

def show_diff(title, d):
    st.markdown(f"**{title}**")
    st.write(f"- Missing: `{d.missing}`")
    st.write(f"- Unexpected: `{d.unexpected}`")
    if d.dtype_mismatch:
        st.write("- Dtype mismatch:")
        for col, got, exp in d.dtype_mismatch:
            st.write(f"  • `{col}`: got `{got}`, expected `{exp}`")
    else:
        st.write("- Dtype mismatch: —")

colA, colB = st.columns(2)
with colA: show_diff("routing_df", rd)
with colB: show_diff("bom_df", bd)

st.markdown("---")
st.subheader("Fix toepassen")

drop = st.checkbox("Verwijder onverwachte kolommen tijdens fix", value=False)

if st.button("🔧 Fix routing_df"):
    fixed, rep = fix_schema(routing_df, ROUTING_SCHEMA, drop_unexpected=drop)
    st.session_state["routing_df"] = fixed
    st.success("routing_df gefixt.")
    st.json({
        "reordered": rep.reordered,
        "filled_defaults": rep.filled_defaults,
        "casted_types": rep.casted_types,
        "dropped_unexpected": rep.dropped_unexpected
    })
    st.dataframe(fixed, use_container_width=True)

if st.button("🔧 Fix bom_df"):
    fixed, rep = fix_schema(bom_df, BOM_SCHEMA, drop_unexpected=drop)
    st.session_state["bom_df"] = fixed
    st.success("bom_df gefixt.")
    st.json({
        "reordered": rep.reordered,
        "filled_defaults": rep.filled_defaults,
        "casted_types": rep.casted_types,
        "dropped_unexpected": rep.dropped_unexpected
    })
    st.dataframe(fixed, use_container_width=True)

st.caption("Tip: draai deze check na het laden van presets of import via Excel/CSV om schema-drift te voorkomen.")
