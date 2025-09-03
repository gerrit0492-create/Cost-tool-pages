# tools/auto_inject_bootstrap.py
from pathlib import Path

HEADER = "from bootstrap import configure_page, init_state\nconfigure_page(); init_state()\n\n"
targets = [Path("home.py")] + sorted(Path("pages").glob("*.py"))

for p in targets:
    txt = p.read_text(encoding="utf-8")
    if "configure_page();" in txt:
        continue
    # Inject bovenaan, maar na event. shebang/encoding
    lines = txt.splitlines(True)
    insert_at = 0
    if lines and lines[0].startswith("#!"):
        insert_at = 1
    if lines and "coding:" in lines[0]:
        insert_at = 1
    lines.insert(insert_at, HEADER)
    p.write_text("".join(lines), encoding="utf-8")
    print(f"Injected bootstrap header in {p}")
