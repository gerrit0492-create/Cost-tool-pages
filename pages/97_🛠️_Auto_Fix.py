# pages/97_🛠️_Auto_Fix.py
from __future__ import annotations
import sys, json, base64
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="🛠️ Auto-Fix", page_icon="🛠️", layout="wide")
st.title("🛠️ Auto-Fix: automatisch issues oplossen")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Probeer de tool te importeren
tool_mod = None
tool_err = None
try:
    from tools.auto_fix import iter_py_files, process_file  # type: ignore
except Exception as e:
    tool_err = e

if tool_err:
    st.error("Kan `tools/auto_fix.py` niet importeren.")
    st.code(str(tool_err))
    st.info("Maak het bestand aan op: tools/auto_fix.py (gebruik de versie die ik eerder stuurde).")
    st.stop()

st.caption("Deze pagina kan je code scannen (dry-run) en automatisch fixes toepassen. "
           "Onthoud: wijzigingen zijn tijdelijk op Streamlit Cloud, **push** ze naar GitHub om te bewaren.")

# --- UI: opties ---
colA, colB = st.columns([2,1])
with colA:
    filter_sub = st.text_input("Filter (alleen bestanden waarvan het pad dit bevat)", value="")
with colB:
    mode = st.radio("Modus", ["Dry-run (alleen diff tonen)", "Toepassen (schrijf wijzigingen)"], horizontal=False)

st.divider()

# --- Acties ---
c1, c2 = st.columns(2)
run_dry = c1.button("🔍 Scan & toon diffs")
run_apply = c2.button("🔧 Toepassen (schrijf wijzigingen)")

def _run_autofix(apply: bool):
    files = [p for p in iter_py_files(ROOT) if filter_sub in str(p)]
    if not files:
        st.info("Geen .py bestanden gevonden met deze filter.")
        return [], []

    changed = []
    messages = []

    for p in files:
        ok, msg = process_file(p, apply=apply)
        messages.append((p, ok, msg))
        if ok and "Gewijzigd:" in msg:
            changed.append(p)

    # Presentatie
    for p, ok, msg in messages:
        with st.expander(str(p.relative_to(ROOT)), expanded=not apply):
            if not ok:
                st.error(msg)
            else:
                if apply:
                    st.write(msg)
                else:
                    # diff tonen
                    st.code(msg, language="diff")

    return files, changed

changed_files = []
if run_dry or (mode.startswith("Dry") and run_apply):  # beveiliging als iemand 'apply' klikt maar modus Dry is
    st.subheader("🔎 Resultaten (dry-run)")
    _files, _changed = _run_autofix(apply=False)
elif run_apply and mode.startswith("Toepassen"):
    st.subheader("🔧 Wijzigingen toegepast")
    _files, changed_files = _run_autofix(apply=True)

st.divider()
st.subheader("💾 Optioneel: wijzigingen naar GitHub pushen")

st.caption("Vul onderstaande velden in om gewijzigde bestanden te **committen** naar je repo. "
           "Je token heeft minimaal *repo*-scope nodig. Bestanden worden via de GitHub Contents API geüpdatet.")

# Prefill uit secrets (als je die hebt gezet)
owner = st.text_input("Owner/Org", value=st.secrets.get("GH_OWNER", ""))
repo  = st.text_input("Repository", value=st.secrets.get("GH_REPO", ""))
branch= st.text_input("Branch", value=st.secrets.get("GH_BRANCH", "main"))
token = st.text_input("GitHub Token", value=st.secrets.get("GITHUB_TOKEN", ""), type="password")
commit_msg = st.text_input("Commit message", value="auto-fix: streamlit hygiene & widget keys")

# Kies wat je wilt pushen
push_mode = st.radio("Welke bestanden pushen?", ["Alle gewijzigde bestanden (deze sessie)",
                                                 "Handmatig selecteren"], horizontal=True)

files_to_push = []
if push_mode.startswith("Alle"):
    files_to_push = changed_files
    if not files_to_push:
        st.info("Nog geen lijst met ‘gewijzigde bestanden’. Voer eerst **Toepassen** uit.")
else:
    # laat gebruiker kiezen uit repo-bestanden
    all_py = [p for p in iter_py_files(ROOT)]
    sel = st.multiselect("Bestanden om te pushen", [str(p.relative_to(ROOT)) for p in all_py])
    files_to_push = [ROOT / s for s in sel]

def github_get_sha(owner, repo, branch, path, token):
    import requests
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"} if token else {},
                     params={"ref": branch}, timeout=20)
    if r.status_code == 200:
        try:
            return r.json().get("sha")
        except Exception:
            return None
    return None

def github_put_file(owner, repo, branch, path, token, content_bytes, message):
    import requests
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    sha = github_get_sha(owner, repo, branch, path, token)
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("ascii"),
        "branch": branch
    }
    if sha:
        payload["sha"] = sha
    headers = {"Accept":"application/vnd.github+json",
               "Authorization": f"Bearer {token}"} if token else {"Accept":"application/vnd.github+json"}
    r = requests.put(url, headers=headers, json=payload, timeout=30)
    ok = r.status_code in (200, 201)
    return ok, (r.json() if ok else f"{r.status_code} {r.text}")

push = st.button("⬆️ Push naar GitHub")
if push:
    if not (owner and repo and branch and token and commit_msg and files_to_push):
        st.error("Vul owner/repo/branch/token/commit message in én kies bestanden.")
    else:
        results = []
        for f in files_to_push:
            rel = str(f.relative_to(ROOT)).replace("\\", "/")
            try:
                data = f.read_text(encoding="utf-8").encode("utf-8")
                ok, resp = github_put_file(owner, repo, branch, rel, token, data, commit_msg)
                results.append({"file": rel, "ok": ok, "resp": resp if ok else str(resp)})
            except Exception as e:
                results.append({"file": rel, "ok": False, "resp": f"read error: {e}"})
        st.success("Push voltooid (zie resultaten hieronder).")
        st.json(results)

st.markdown("---")
st.caption("Tip: na **Toepassen** kun je snel valideren met de pagina’s **🩺 App Check** en **🧪 Schema Check**.")
