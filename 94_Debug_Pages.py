import streamlit as st, pathlib as pl, importlib.util, traceback

st.title("🔍 Debug alle pages")

root = pl.Path(__file__).resolve().parents[1] / "pages"
errors = []

for page in sorted(root.glob("*.py")):
    if page.name.startswith("98_") or page.name.startswith("99_"):
        continue
    try:
        spec = importlib.util.spec_from_file_location(page.stem, page)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        tb = "".join(traceback.format_exception_only(type(e), e)).strip()
        errors.append((page, tb))

if not errors:
    st.success("Alle pages importeren correct ✅")
else:
    st.error(f"{len(errors)} pages gooien een fout:")
    for p, msg in errors:
        st.code(f"{p}\n{msg}")
