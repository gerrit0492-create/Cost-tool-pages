import streamlit as st, pathlib as pl, traceback

st.title("🧪 Syntax Check")
root = pl.Path(__file__).resolve().parents[1]

problems = []
for p in sorted(root.rglob("*.py")):
    if p.name == "99_Syntax_Check.py": 
        continue
    try:
        src = p.read_text(encoding="utf-8")
        compile(src, str(p), "exec")
    except SyntaxError as e:
        problems.append((p, f"{e.__class__.__name__}: {e.msg} at {e.filename}:{e.lineno}:{e.offset}\n{e.text}"))
    except Exception as e:
        # runtime import errors etc. zijn geen SyntaxError, maar tonen we ook
        tb = "".join(traceback.format_exception_only(type(e), e)).strip()
        problems.append((p, f"{type(e).__name__}: {tb}"))

if not problems:
    st.success("Geen SyntaxErrors gevonden 🎉")
else:
    st.error(f"{len(problems)} probleem(en) gevonden:")
    for p, msg in problems:
        st.code(f"{p}\n{msg}")
