# bootstrap.py (in repo-root)
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Zet repo-root helemaal vooraan, vóór site-packages:
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Beetje sanity: voorkom schaduwing door een verdwaalde 'utils.py' etc.
for shady in ("utils.py", "shared.py"):
    p = ROOT / shady
    if p.exists():
        raise RuntimeError(
            f"Bestand {shady} in repo-root schaduwt je package-map. "
            f"Verwijder/hernoem {p}."
        )
