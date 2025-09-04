#!/usr/bin/env python3
from __future__ import annotations
import ast, io, os, re, sys, difflib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[1]

WIDGET_FUNCS = {
    "button", "checkbox", "radio", "selectbox", "multiselect",
    "slider", "text_input", "number_input", "file_uploader",
    "data_editor", "toggle", "date_input", "time_input", "color_picker"
}

DEBUG_PATTERNS = [
    "sys.path[0:3]", "root files", "utils files",
    "st.write(\"sys.path", "st.write('sys.path",
    "st.code(\"sys.path", "st.json(\"sys.path"
]

NET_FUNCS = {("requests","get"), ("requests","post"), ("urllib.request","urlopen")}

@dataclass
class Edit:
    lineno: int
    old: str
    new: str
    note: str

class Analyzer(ast.NodeVisitor):
    def __init__(self, src: str):
        self.src = src
        self.streamlit_calls: List[Tuple[int,str]] = []
        self.set_page_config_lines: List[int] = []
        self.widget_calls: List[Tuple[int,str,bool]] = []  # (lineno, fullname, has_key)
        self.top_level_net: List[Tuple[int,str]] = []
        self.depth = 0
        super().__init__()

    def visit_FunctionDef(self, node): self.depth += 1; self.generic_visit(node); self.depth -= 1
    visit_AsyncFunctionDef = visit_FunctionDef
    def visit_Lambda(self, node): self.depth += 1; self.generic_visit(node); self.depth -= 1

    def visit_Call(self, node: ast.Call):
        fullname = None
        if isinstance(node.func, ast.Attribute):
            parts = []
            cur = node.func
            while isinstance(cur, ast.Attribute):
                parts.insert(0, cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.insert(0, cur.id)
            fullname = ".".join(parts)

        if fullname and fullname.startswith("st."):
            self.streamlit_calls.append((node.lineno, fullname))
            if fullname == "st.set_page_config":
                self.set_page_config_lines.append(node.lineno)
            fn = fullname.split(".",1)[1]
            if fn in WIDGET_FUNCS:
                has_key = any((isinstance(kw, ast.keyword) and kw.arg == "key") for kw in node.keywords)
                self.widget_calls.append((node.lineno, fn, has_key))

        if fullname:
            for base, meth in NET_FUNCS:
                if fullname == f"{base}.{meth}" and self.depth == 0:
                    self.top_level_net.append((node.lineno, fullname))

        self.generic_visit(node)

def uniquify_key(base: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", base)

def add_or_move_set_page_config(lines: List[str]) -> List[Edit]:
    edits = []
    # Zoek eerste streamlit call
    first_st = None
    spc_lines = []
    for i, line in enumerate(lines, start=1):
        if re.search(r"\bst\.set_page_config\s*\(", line):
            spc_lines.append(i)
        if first_st is None and re.search(r"\bst\.", line):
            first_st = i
    # Al aanwezig en als eerste? niks doen.
    if spc_lines:
        # Laat slechts de eerste bestaan; comment de rest uit
        for ln in spc_lines[1:]:
            old = lines[ln-1]
            edits.append(Edit(ln, old, f"# [auto-fix] {old}", "multiple set_page_config -> commented"))
        # Move naar top als nodig
        if first_st is not None and spc_lines[0] > first_st:
            # Voeg een kopie toe bovenaan na imports; comment oude
            header_idx = 0
            for i, t in enumerate(lines):
                if t.strip().startswith("import ") or t.strip().startswith("from "):
                    header_idx = i+1
            new_line = "st.set_page_config(page_title='App', page_icon='📦', layout='wide')\n"
            edits.append(Edit(header_idx+1, lines[header_idx], lines[header_idx] + new_line, "insert set_page_config near top"))
            old = lines[spc_lines[0]-1]
            edits.append(Edit(spc_lines[0], old, f"# [auto-fix moved] {old}", "comment old set_page_config"))
        return edits
    # Niet gevonden → invoegen na imports
    header_idx = 0
    for i, t in enumerate(lines):
        if t.strip().startswith("import ") or t.strip().startswith("from "):
            header_idx = i+1
    new_line = "st.set_page_config(page_title='App', page_icon='📦', layout='wide')\n"
    edits.append(Edit(header_idx+1, lines[header_idx], lines[header_idx] + new_line, "insert set_page_config"))
    return edits

def add_keys_to_duplicate_widgets(lines: List[str], an: Analyzer, filetag: str) -> List[Edit]:
    edits = []
    # label → lijst van (lineno, has_key)
    pattern = re.compile(r"st\.(%s)\s*\(" % "|".join(map(re.escape, WIDGET_FUNCS)))
    # ruwe heuristic: pak label uit eerste arg als string
    def extract_label_args(s: str):
        m = pattern.search(s)
        if not m: return None
        # pak inhoud tussen ( ... )
        try:
            inner = s.split("(",1)[1]
        except Exception:
            return None
        return inner

    # map label->lines zonder key
    label_map = {}
    for ln, fn, has_key in an.widget_calls:
        if has_key: continue
        src = lines[ln-1]
        inner = extract_label_args(src)
        if not inner: continue
        # haal eerste string literal
        m = re.match(r"\s*([ruRU]?[fF]?[\"'])(.+?)\1", inner)
        label = m.group(2) if m else None
        if not label: continue
        label_map.setdefault((fn, label), []).append(ln)

    # Als label op meerdere plekken voorkomt → voeg key toe
    for (fn, label), occ in label_map.items():
        if len(occ) < 2:  # enkelvoud mag zonder key blijven
            continue
        for ln in occ:
            old = lines[ln-1]
            # als er al een key is (zou niet) skip
            if " key=" in old:
                continue
            key_val = uniquify_key(f"{filetag}_{fn}_{label}_{ln}")
            # injecteer key=... vóór sluitende ')'
            if old.rstrip().endswith(")"):
                new = old.rstrip()[:-1] + f", key='{key_val}')\n"
            else:
                new = old + f", key='{key_val}'"
            edits.append(Edit(ln, old, new, f"add key for duplicate label: {label}"))
    return edits

def comment_debug_prints(lines: List[str]) -> List[Edit]:
    edits = []
    for i, line in enumerate(lines, start=1):
        if any(pat in line for pat in DEBUG_PATTERNS):
            if not line.lstrip().startswith("#"):
                edits.append(Edit(i, line, "# [auto-fix debug] " + line, "comment debug print"))
    return edits

def wrap_top_level_network(lines: List[str], an: Analyzer) -> List[Edit]:
    if not an.top_level_net:
        return []
    edits = []
    # Comment top-level calls en voeg helper toe onderaan
    called_lines = {ln for ln,_ in an.top_level_net}
    for ln in called_lines:
        old = lines[ln-1]
        edits.append(Edit(ln, old, f"# [auto-fix net] {old}", "comment top-level network call"))

    trailer = [
        "\n\n# [auto-fix net] Moved top-level network calls into a guarded function\n",
        "def _run_network_calls__auto_fix():\n",
        "    import requests, urllib.request\n",
        "    # TODO: move original logic here; all requests should have timeout= and error handling\n",
        "    pass\n",
        "\nif __name__ == '__main__':\n",
        "    try:\n",
        "        _run_network_calls__auto_fix()\n",
        "    except Exception as _e:\n",
        "        print('[auto-fix net] error:', _e)\n",
    ]
    edits.append(Edit(len(lines), lines[-1] if lines else "", (lines[-1] if lines else "") + "".join(trailer), "append guard"))
    return edits

def ensure_bootstrap_import(lines: List[str]) -> List[Edit]:
    text = "".join(lines)
    if "from bootstrap import ROOT" in text:
        return []
    # Voeg net na imports toe (zonder breken als bootstrap.py niet bestaat)
    insert_idx = 0
    for i, t in enumerate(lines):
        if t.strip().startswith("import ") or t.strip().startswith("from "):
            insert_idx = i+1
    snippet = "try:\n    from bootstrap import ROOT\nexcept Exception:\n    pass\n"
    return [Edit(insert_idx+1, lines[insert_idx], lines[insert_idx] + snippet, "insert bootstrap import")]

def apply_edits(text: str, edits: List[Edit]) -> str:
    if not edits:
        return text
    # sorteer op lineno, en als zelfde lijn meerdere edits: voer op volgorde uit
    lines = text.splitlines(keepends=True)
    for e in sorted(edits, key=lambda x: (x.lineno, x.note)):
        # guard als file korter is
        if e.lineno - 1 < 0 or e.lineno - 1 >= len(lines):
            continue
        lines[e.lineno - 1] = e.new
    return "".join(lines)

def process_file(path: Path, apply: bool) -> Tuple[bool, str]:
    src = path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        return False, f"⛔ SyntaxError: {path}"
    an = Analyzer(src); an.visit(tree)

    edits: List[Edit] = []
    lines = src.splitlines(keepends=True)

    # 1) set_page_config fixen (alleen voor pagina's die streamlit gebruiken)
    if any(name.startswith("st.") for _, name in an.streamlit_calls):
        edits += add_or_move_set_page_config(lines)

    # 2) duplicate widget labels → keys
    filetag = path.stem
    edits += add_keys_to_duplicate_widgets(lines, an, filetag)

    # 3) debug-prints commenten
    edits += comment_debug_prints(lines)

    # 4) top-level netwerkcalls inpakken
    edits += wrap_top_level_network(lines, an)

    # 5) bootstrap import toevoegen
    edits += ensure_bootstrap_import(lines)

    if not edits:
        return True, f"✓ Geen wijzigingen nodig: {path}"

    new_src = apply_edits(src, edits)

    if not apply:
        diff = difflib.unified_diff(
            src.splitlines(keepends=True),
            new_src.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path)+" (auto-fix)",
        )
        return True, "".join(diff)

    # Backup en schrijf
    backup = path.with_suffix(path.suffix + ".bak")
    backup.write_text(src, encoding="utf-8")
    path.write_text(new_src, encoding="utf-8")
    return True, f"🔧 Gewijzigd: {path}  (backup: {backup.name})"

def iter_py_files(root: Path) -> List[Path]:
    folders = [root, root/"pages", root/"utils"]
    out: List[Path] = []
    for f in folders:
        if f.exists():
            out += [p for p in f.rglob("*.py") if "__pycache__" not in str(p) and ".venv" not in str(p)]
    return sorted(out)

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Auto-fix voor Streamlit app issues")
    ap.add_argument("--apply", action="store_true", help="Wijzigingen daadwerkelijk schrijven (anders: dry-run diff)")
    ap.add_argument("--filter", type=str, default="", help="Alleen bestanden met dit substring in pad")
    args = ap.parse_args()

    files = [p for p in iter_py_files(ROOT) if args.filter in str(p)]
    if not files:
        print("Geen .py bestanden gevonden.")
        sys.exit(0)

    had_err = False
    for p in files:
        ok, msg = process_file(p, apply=args.apply)
        if not ok:
            had_err = True
        print(msg)

    sys.exit(1 if had_err else 0)

if __name__ == "__main__":
    main()
