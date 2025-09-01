# pages/03_Presets.py
import os, sys, json, io, base64, requests, streamlit as st
from datetime import datetime

# ---- Zorg dat repo-root importeerbaar is ----
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

# ---- Basis pagina ----
st.set_page_config(page_title="Presets & GitHub", page_icon="📁", layout="wide")
st.title("📁 Presets & 🔧 GitHub")

st.caption("""
Gebruik deze pagina om **presets (JSON)** te bewaren of te laden, en om bestanden **rechtstreeks** naar GitHub te pushen.
""")

# -----------------------
# Helper: session snapshot
# -----------------------
def snapshot_from_session():
    """Pak de relevante inputs uit session_state (voeg hier velden toe als je meer wilt bewaren)."""
    keys = [
        "project","Q","mat","netkg","price","price_src",
        "energy","storage_days","storage_cost","km","eur_km",
        "rework","rework_min",
        "routing_df","bom_df"
    ]
    snap = {}
    for k in keys:
        v = st.session_state.get(k)
        # DataFrames → naar dict records
        if hasattr(v, "to_dict"):
            v = v.to_dict(orient="records")
        snap[k] = v
    snap["_meta"] = {"ts": datetime.utcnow().isoformat() + "Z", "app": "maakindustrie-cost-tool-multipage"}
    return snap

def apply_preset_to_session(preset: dict):
    """Schrijf preset terug in session_state."""
    import pandas as pd
    for k, v in preset.items():
        if k in ("routing_df","bom_df") and isinstance(v, list):
            st.session_state[k] = pd.DataFrame(v)
        elif k.startswith("_"):  # meta
            continue
        else:
            st.session_state[k] = v


# -----------------------
# Sectie: Preset opslaan
# -----------------------
st.subheader("Preset opslaan (JSON)")

col_a, col_b = st.columns([2,1])
with col_a:
    default_name = f"{st.session_state.get('project','Preset')}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    fname = st.text_input("Bestandsnaam", default_name)

snap = snapshot_from_session()
json_bytes = json.dumps(snap, indent=2, ensure_ascii=False).encode("utf-8")

with col_b:
    st.download_button(
        "⬇️ Download preset (JSON)",
        data=json_bytes,
        file_name=fname or "preset.json",
        mime="application/json"
    )

with st.expander("Preview JSON (alleen lezen)"):
    st.code(json.dumps(snap, indent=2, ensure_ascii=False), language="json")


# -----------------------
# Sectie: Preset laden
# -----------------------
st.subheader("Preset laden")

up = st.file_uploader("Upload preset JSON", type=["json"])
if up is not None:
    try:
        preset = json.load(up)
        apply_preset_to_session(preset)
        st.success("Preset geladen en toegepast op de sessie. Ga naar **Calculatie** om het resultaat te zien.")
    except Exception as e:
        st.error(f"Kon preset niet laden: {e}")


st.markdown("---")

# =======================
# GitHub integratie
# =======================

st.header("🔧 GitHub: bestanden pushen (create/update)")

st.caption("""
Vul je **repo**, **pad** en **token** in om bestanden te uploaden of bij te werken.
Je token wordt **niet opgeslagen**. Voor productie: zet `GITHUB_TOKEN` in `.streamlit/secrets.toml`.
""")

# Prefill uit secrets als aanwezig
default_owner = st.secrets.get("GH_OWNER", "")
default_repo  = st.secrets.get("GH_REPO", "")
default_branch= st.secrets.get("GH_BRANCH", "main")
default_token = st.secrets.get("GITHUB_TOKEN", "")

col1, col2, col3 = st.columns(3)
with col1:
    gh_owner = st.text_input("Owner / org", default_owner or "gerrit0492-create")
with col2:
    gh_repo  = st.text_input("Repo", default_repo or "maakindustrie-cost-tool-multipage")
with col3:
    gh_branch= st.text_input("Branch", default_branch or "main")

tok_col, path_col = st.columns([1,2])
with tok_col:
    gh_token = st.text_input("GitHub token (repo scope)", value=default_token, type="password")
with path_col:
    target_path = st.text_input("Pad in repo (bijv. `presets/demo.json` of `exports/rapport.pdf`)", "presets/preset.json")

st.caption("Je kunt óf de **huidige preset** pushen, óf een **eigen bestand** uploaden en pushen.")

# Optie 1: push de huidige preset (JSON)
def github_get_sha(owner, repo, branch, path, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    params = {"ref": branch}
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.get(url, headers=headers, params=params, timeout=20)
    if r.status_code == 200:
        return r.json().get("sha")
    return None

def github_put_file(owner, repo, branch, path, token, content_bytes, message):
    """Create or update a file via GitHub API (base64 content, with SHA if exists)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}" if token else "",
    }
    # Ophalen SHA (als bestand bestaat)
    current_sha = github_get_sha(owner, repo, branch, path, token)

    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("ascii"),
        "branch": branch
    }
    if current_sha:
        payload["sha"] = current_sha

    r = requests.put(url, headers=headers, json=payload, timeout=30)
    if r.status_code in (200,201):
        return True, r.json()
    else:
        return False, f"{r.status_code} {r.text}"

colp1, colp2 = st.columns(2)

if colp1.button("⬆️ Push huidige preset (JSON)"):
    if not gh_owner or not gh_repo or not gh_branch or not gh_token or not target_path:
        st.error("Vul owner, repo, branch, token en pad in.")
    else:
        ok, resp = github_put_file(
            gh_owner, gh_repo, gh_branch, target_path, gh_token,
            json_bytes, message=f"Add/update preset via app ({datetime.utcnow().isoformat()}Z)"
        )
        if ok:
            st.success("Preset geüpload naar GitHub.")
            st.json({"path": target_path, "repo": f"{gh_owner}/{gh_repo}", "branch": gh_branch})
        else:
            st.error(f"GitHub push mislukt: {resp}")

# Optie 2: upload willekeurig bestand en push
uploaded_any = colp2.file_uploader("Upload bestand om naar GitHub te pushen", type=None, key="anyfile")
if uploaded_any is not None:
    any_bytes = uploaded_any.read()
    push_name = st.text_input("Opslaan als (pad/bestandsnaam in repo)", f"uploads/{uploaded_any.name}")
    if st.button("⬆️ Push geüpload bestand"):
        if not gh_owner or not gh_repo or not gh_branch or not gh_token or not push_name:
            st.error("Vul owner, repo, branch, token en doelpad in.")
        else:
            ok, resp = github_put_file(
                gh_owner, gh_repo, gh_branch, push_name, gh_token,
                any_bytes, message=f"Upload via app ({datetime.utcnow().isoformat()}Z)"
            )
            if ok:
                st.success("Bestand geüpload naar GitHub.")
                st.json({"path": push_name, "repo": f"{gh_owner}/{gh_repo}", "branch": gh_branch})
            else:
                st.error(f"GitHub push mislukt: {resp}")

st.markdown("---")

# -----------------------
# GitHub → preset terughalen
# -----------------------
st.subheader("Preset laden vanaf GitHub")

colg1, colg2 = st.columns(2)
with colg1:
    gh_path_load = st.text_input("Pad naar preset in repo", "presets/preset.json")
with colg2:
    load_btn = st.button("⬇️ Laden en toepassen")

def github_get_raw(owner, repo, branch, path, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    params = {"ref": branch}
    r = requests.get(url, headers=headers, params=params, timeout=20)
    if r.status_code != 200:
        return None, f"{r.status_code} {r.text}"
    j = r.json()
    if "content" in j:
        try:
            b = base64.b64decode(j["content"])
            return b, "ok"
        except Exception as e:
            return None, f"decode error: {e}"
    return None, "no content"

if load_btn:
    if not gh_owner or not gh_repo or not gh_branch or not gh_path_load:
        st.error("Vul owner, repo, branch en pad in.")
    else:
        raw, msg = github_get_raw(gh_owner, gh_repo, gh_branch, gh_path_load, gh_token)
        if raw is None:
            st.error(f"Kon preset niet ophalen: {msg}")
        else:
            try:
                preset = json.loads(raw.decode("utf-8"))
                apply_preset_to_session(preset)
                st.success("Preset uit GitHub geladen en toegepast. Ga naar **Calculatie**.")
                with st.expander("Inhoud preset"):
                    st.code(json.dumps(preset, indent=2, ensure_ascii=False), language="json")
            except Exception as e:
                st.error(f"JSON kon niet worden gelezen: {e}")p
