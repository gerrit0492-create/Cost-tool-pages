# pages/10_Webhooks_API.py
import os, sys, io, json, base64, requests, traceback
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Webhooks & API", page_icon="🛰️", layout="wide")
st.title("🛰️ Webhooks & API (GitHub-inbox + snelle exports)")

st.caption("""
Deze pagina geeft je een **eenvoudige webhook-inbox** via GitHub (map met JSON/CSV payloads), en **API-achtige exports** 
van je huidige sessie (JSON/CSV) die je elders kunt consumeren. Geen extra server nodig.
""")

# ---------------------------
# Basis: GitHub-inbox helper
# ---------------------------
def gh_headers(token: str|None):
    h = {"Accept":"application/vnd.github+json"}
    if token: h["Authorization"] = f"Bearer {token}"
    return h

def gh_list_dir(owner, repo, branch, path, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    r = requests.get(url, headers=gh_headers(token), params={"ref": branch}, timeout=20)
    if r.status_code == 200:
        return r.json(), None
    return None, f"{r.status_code} {r.text}"

def gh_get_file(owner, repo, branch, path, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    r = requests.get(url, headers=gh_headers(token), params={"ref": branch}, timeout=20)
    if r.status_code != 200:
        return None, f"{r.status_code} {r.text}"
    j = r.json()
    if "content" in j:
        try:
            raw = base64.b64decode(j["content"])
            return raw, {"sha": j.get("sha")}
        except Exception as e:
            return None, f"decode error: {e}"
    return None, "no content"

def gh_put_file(owner, repo, branch, path, token, content_bytes, message, sha=None):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("ascii"),
        "branch": branch
    }
    if sha: payload["sha"] = sha
    r = requests.put(url, headers=gh_headers(token), json=payload, timeout=30)
    if r.status_code in (200,201): return True, r.json()
    return False, f"{r.status_code} {r.text}"

def gh_move_file(owner, repo, branch, src_path, dst_path, token, commit_msg="Move"):
    # GitHub API kent geen 'move'; we doen: read dst sha (indien), create dst, delete src
    raw, meta = gh_get_file(owner, repo, branch, src_path, token)
    if raw is None: return False, f"cannot read {src_path}"
    ok, resp = gh_put_file(owner, repo, branch, dst_path, token, raw, f"{commit_msg}: {src_path} -> {dst_path}")
    if not ok: return False, resp
    # delete src
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{src_path}"
    r = requests.delete(url, headers=gh_headers(token),
                        json={"message":f"Delete {src_path} after move","branch":branch,"sha": meta.get("sha")}, timeout=20)
    if r.status_code in (200,204): return True, "ok"
    return False, f"{r.status_code} {r.text}"

# ---------------------------
# Instellingen (secrets of form)
# ---------------------------
st.subheader("GitHub-inbox configureren")
c1,c2,c3,c4 = st.columns(4)
with c1: gh_owner = st.text_input("Owner/org", st.secrets.get("GH_OWNER","gerrit0492-create"))
with c2: gh_repo  = st.text_input("Repo",      st.secrets.get("GH_REPO","maakindustrie-cost-tool-multipage"))
with c3: gh_branch= st.text_input("Branch",    st.secrets.get("GH_BRANCH","main"))
with c4: gh_token = st.text_input("Token (repo)", st.secrets.get("GITHUB_TOKEN",""), type="password")

c5,c6 = st.columns(2)
with c5: inbox_path  = st.text_input("Inbox pad (map)", "inbox")
with c6: done_path   = st.text_input("Processed pad (map)", "inbox/processed")

st.caption("Webhook: laat externe systemen een JSON of CSV **committen** naar jouw repo in `inbox/`. Je leest/verwerkt ze hier, en verplaatst ze daarna naar `inbox/processed/`.")

# ---------------------------
# Inbox bekijken
# ---------------------------
st.markdown("### 📬 Inbox inhoud")
if st.button("🔄 Refresh inbox"):
    st.session_state["_inbox_refresh"] = True

try:
    items, err = gh_list_dir(gh_owner, gh_repo, gh_branch, inbox_path, gh_token)
    if err:
        st.error(f"Inbox niet leesbaar: {err}")
        items = []
except Exception:
    st.error("Fout bij lezen inbox.")
    st.code("".join(traceback.format_exc()))
    items = []

files = []
for it in items or []:
    if it.get("type") == "file":
        name = it.get("name","")
        if name.lower().endswith((".json",".csv")):
            files.append(it)

if files:
    st.success(f"Gevonden bestanden: {len(files)}")
    st.dataframe(pd.DataFrame([{"name":f["name"],"size":f.get("size"),"path":f.get("path")} for f in files]),
                 use_container_width=True)
else:
    st.info("Geen JSON/CSV gevonden in inbox.")

# ---------------------------
# Bestanden openen & verwerken
# ---------------------------
st.markdown("### 🔎 Bestand openen")
sel = st.selectbox("Kies een bestand", [f["path"] for f in files] if files else [])
if sel:
    raw, meta = gh_get_file(gh_owner, gh_repo, gh_branch, sel, gh_token)
    if raw is None:
        st.error(f"Kan {sel} niet lezen.")
    else:
        if sel.lower().endswith(".json"):
            try:
                data = json.loads(raw.decode("utf-8"))
                st.json(data)
                # simpele mapping naar BOM/Routing (optioneel)
                if isinstance(data, dict):
                    if st.button("⬇️ Zet in sessie (indien velden aanwezig)"):
                        import pandas as pd
                        if "routing_df" in data and isinstance(data["routing_df"], list):
                            st.session_state["routing_df"] = pd.DataFrame(data["routing_df"])
                        if "bom_df" in data and isinstance(data["bom_df"], list):
                            st.session_state["bom_df"] = pd.DataFrame(data["bom_df"])
                        for k in ["project","Q","mat","netkg","price","price_src"]:
                            if k in data: st.session_state[k] = data[k]
                        st.success("Gegevens toegepast op sessie. Ga naar **Calculatie**.")
            except Exception as e:
                st.error(f"JSON parse fout: {e}")
        elif sel.lower().endswith(".csv"):
            try:
                df = pd.read_csv(io.BytesIO(raw))
                st.dataframe(df, use_container_width=True)
                dest = st.radio("Interpretatie", ["BOM","Routing","Onbekend"], horizontal=True)
                if st.button("⬇️ Zet in sessie als geselecteerde tabel"):
                    if dest=="BOM":
                        st.session_state["bom_df"] = df
                        st.success("BOM bijgewerkt uit CSV.")
                    elif dest=="Routing":
                        st.session_state["routing_df"] = df
                        st.success("Routing bijgewerkt uit CSV.")
            except Exception as e:
                st.error(f"CSV leesfout: {e}")

        # verplaatsen naar processed
        st.markdown("---")
        new_name = st.text_input("Nieuwe bestandsnaam in processed/", value=os.path.basename(sel))
        if st.button("✅ Markeer als verwerkt (move)"):
            ok, resp = gh_move_file(gh_owner, gh_repo, gh_branch, sel, f"{done_path}/{new_name}", gh_token,
                                    commit_msg="Processed via app")
            if ok: st.success("Bestand verplaatst naar processed.")
            else:  st.error(f"Move mislukt: {resp}")

# ---------------------------
# API-achtige export (live)
# ---------------------------
st.markdown("---")
st.header("⚡ Snelle API-export (JSON/CSV)")

def session_snapshot():
    keys = ["project","Q","mat","netkg","price","price_src","routing_df","bom_df"]
    snap={}
    for k in keys:
        v = st.session_state.get(k)
        if hasattr(v, "to_dict"):
            v = v.to_dict(orient="records")
        snap[k] = v
    snap["_meta"] = {"ts": datetime.utcnow().isoformat() + "Z"}
    return snap

snap = session_snapshot()
json_bytes = json.dumps(snap, indent=2, ensure_ascii=False).encode("utf-8")
st.download_button("⬇️ Download JSON (sessie)", json_bytes, "session_export.json", "application/json")

# CSV’s (BOM/Routing)
import pandas as pd
bom_df = pd.DataFrame(st.session_state.get("bom_df") or [])
rout_df= pd.DataFrame(st.session_state.get("routing_df") or [])
c1,c2 = st.columns(2)
c1.download_button("⬇️ Download BOM (CSV)", bom_df.to_csv(index=False).encode("utf-8"),
                   "session_BOM.csv","text/csv")
c2.download_button("⬇️ Download Routing (CSV)", rout_df.to_csv(index=False).encode("utf-8"),
                   "session_Routing.csv","text/csv")

st.info("""
Wil je deze exports **automatisch naar GitHub** pushen zodat anderen ze als **Raw URL** kunnen benaderen? 
Gebruik pagina **03_Presets & GitHub** om te pushen naar bijv. `exports/session.json` of `exports/BOM.csv`.
""")
