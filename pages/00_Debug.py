import streamlit as st, ast, pathlib

st.title("Syntax check")
out = []
def check_file(p):
    try:
        src = p.read_text(encoding="utf-8")
        ast.parse(src, filename=str(p))
        out.append(("OK", str(p), ""))
    except SyntaxError as e:
        out.append(("SYNTAXERROR", f"{p}:{e.lineno}:{e.offset}", e.msg))

paths = [pathlib.Path("home.py")] + sorted(pathlib.Path("pages").glob("*.py"))
for p in paths:
    if p.exists(): check_file(p)

for status, where, msg in out:
    st.write(f"**{status}** — {where} — {msg}")
