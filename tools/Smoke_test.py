# tools/smoke_test.py
from __future__ import annotations
import pathlib, py_compile, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGES = ROOT / "pages"

def main() -> int:
    errors = []
    for p in sorted(PAGES.glob("*.py")):
        try:
            py_compile.compile(str(p), doraise=True)
            print(f"[ok]  {p.name}")
        except Exception as e:
            print(f"[ERR] {p.name}: {type(e).__name__}: {e}")
            errors.append((p.name, e))
    if errors:
        print("\nFailures:")
        for n, e in errors:
            print(f" - {n}: {e}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
