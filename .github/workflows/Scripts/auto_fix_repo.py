# .github/workflows/scripts/auto_fix_repo.py
from __future__ import annotations
import pathlib as pl, re

ROOT = pl.Path(".")
PAGES = ROOT / "pages"

# Regels:
# 1) Oude imports -> nieuwe (utils.io) + laat utils.shared voor compat bestaan
IMPORT_OLD = re.compile(r"from\s+utils\.shared\s+import\s+([^\n]+)")
RENAME_MAP = {
    "MATERIALS": "SCHEMA_MATERIALS",
    "PROCESSES": "SCHEMA_PROCESSES",
    "BOM": "SCHEMA_BOM",
}

# 2) Voeg guard in: wrap main() aan het eind als guard(main) nog niet voorkomt
HAS_GUARD = re.compile(r"\bguard\s*\(\s*main\s*\)\s*$", re.M)

# 3) Vervang Δ-karakters en andere unicode operators die syntax/encodings gedoe geven
UNICODE_FIXES = {
    "Δ": "delta_",
    "–": "-",  # en-dash -> minus
    "—": "-",  # em-dash -> minus
    "’": "'",
    "“": '"',
    "”": '"',
    "•": "-",
}

def normalize_unicode(s: str) -> str:
    for bad, good in UNICODE_FIXES.items():
        s = s.replace(bad, good)
    return s

def fix_imports(src: str) -> str:
    # als file al uit utils.io importeert, niets doen
    if "from utils.io import" in src:
        return src

    m = IMPORT_OLD.search(src)
    if not m:
        return src

    items = [i.strip() for i in m.group(1).split(",")]
    mapped = []
    passthrough = []
    for it in items:
        name = it.split(" as ")[0].strip()
        if name in RENAME_MAP:
            mapped.append(f"{RENAME_MAP[name]} as {name}")
        elif name in ("read_csv_safe", "paths"):
            passthrough.append(name)
        # anders laten we 'm weg; die komt al uit utils/shared.py compat

    blocks = []
    if mapped or passthrough:
        imp = []
        if mapped:
            imp.extend(mapped)
        if passthrough:
            imp.extend(passthrough)
        blocks.append("from utils.io import (\n    " + ",\n    ".join(imp) + "\n)")
    # verwijder oude regel
    src = IMPORT_OLD.sub("\n".join(blocks) if blocks else "", src)
    return src

def ensure_guard(src: str) -> str:
    if "def main(" not in src:
        return src
    if HAS_GUARD.search(src):
        return src
    # voeg guard import toe als hij ontbreekt
    if "from utils.safe import guard" not in src and "import utils.safe" not in src:
        # injecteer import na eerste streamlit/pandas import
        lines = src.splitlines()
        inserted = False
        for i, line in enumerate(lines[:30]):
            if line.startswith("import streamlit") or line.startswith("from bootstrap"):
                lines.insert(i+1, "from utils.safe import guard")
                inserted = True
                break
        if not inserted:
            lines.insert(0, "from utils.safe import guard")
        src = "\n".join(lines)
    # voeg guard(main) toe onderin
    if src.endswith("\n"):
        return src + "\n\nguard(main)\n"
    else:
        return src + "\n\nguard(main)\n"

def process_file(p: pl.Path) -> bool:
    original = p.read_text(encoding="utf-8")
    s = original
    s = normalize_unicode(s)
    s = fix_imports(s)
    s = ensure_guard(s)
    if s != original:
        p.write_text(s, encoding="utf-8")
        return True
    return False

def main():
    changed = 0
    for p in sorted(PAGES.glob("*.py")):
        if p.name.startswith(("98_", "99_")):
            continue
        try:
            if process_file(p):
                print(f"Fixed: {p}")
                changed += 1
        except Exception as e:
            print(f"Skip {p}: {e}")
    print(f"Done. Files changed: {changed}")

if __name__ == "__main__":
    main()
