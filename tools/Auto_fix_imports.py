# tools/auto_fix_imports.py
from __future__ import annotations
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGETS = ["pages", "utils"]

# Regels: (pattern -> replacement)
REWRITES = [
    # Oude shared-aliasen naar compat
    (r"from\s+utils\.shared\s+import\s+MATERIALS\b", "from utils.compat import SCHEMA_MATERIALS as MATERIALS"),
    (r"from\s+utils\.shared\s+import\s+PROCESSES\b", "from utils.compat import SCHEMA_PROCESSES as PROCESSES"),
    (r"from\s+utils\.shared\s+import\s+BOM\b", "from utils.compat import SCHEMA_BOM as BOM"),

    # Alles uit io -> io (blijft), maar fallback naar compat als breed
    (r"from\s+utils\.io\s+import\s+\(([^)]+)\)", r"from utils.io import (\1)"),
    (r"from\s+utils\.shared\s+import\s+\(([^)]+)\)", r"from utils.shared import (\1)"),

    # Sommige code importeerde direct schema’s uit shared; stuur door naar compat
    (r"from\s+utils\.shared\s+import\s+SCHEMA_MATERIALS", "from utils.compat import SCHEMA_MATERIALS"),
    (r"from\s+utils\.shared\s+import\s+SCHEMA_PROCESSES", "from utils.compat import SCHEMA_PROCESSES"),
    (r"from\s+utils\.shared\s+import\s+SCHEMA_BOM", "from utils.compat import SCHEMA_BOM"),
]

def rewrite_text(txt: str) -> tuple[str, bool]:
    original = txt
    for pat, repl in REWRITES:
        txt = re.sub(pat, repl, txt)
    changed = (txt != original)
    return txt, changed

def ensure_guard(txt: str) -> str:
    if "from utils.safe import guard" not in txt:
        # Voeg bovenaan toe (na eventuele future-import)
        lines = txt.splitlines()
        insert_at = 0
        if lines and lines[0].startswith("from __future__"):
            insert_at = 1
        lines.insert(insert_at, "from utils.safe import guard")
        return "\n".join(lines) + ("\n" if not txt.endswith("\n") else "")
    return txt

def process_file(path: pathlib.Path) -> bool:
    if path.suffix != ".py":
        return False
    txt = path.read_text(encoding="utf-8")
    new, changed = rewrite_text(txt)
    new = ensure_guard(new)
    if new != txt:
        path.write_text(new, encoding="utf-8")
        print(f"[fix] {path.relative_to(ROOT)}")
        return True
    return False

def main() -> int:
    any_change = False
    for folder in TARGETS:
        base = ROOT / folder
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            if p.name.startswith("_"):
                continue
            if process_file(p):
                any_change = True
    if not any_change:
        print("No changes needed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
