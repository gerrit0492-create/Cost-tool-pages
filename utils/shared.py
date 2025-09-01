# bovenin elk .py bestand
import streamlit as st, traceback

def guard(run):
    try:
        run()
    except Exception:
        err = traceback.format_exc()
        # toon in UI
        st.exception(err)
        # bewaar ook in session_state zodat Diagnose-pagina hem kan tonen
        st.session_state["last_exception"] = err
# utils/shared.py — gedeelde logica
import re, numpy as np, pandas as pd, requests, streamlit as st

# ---- Constanten / stamdata ----
HEADERS={"User-Agent":"Mozilla/5.0 (CostTool/1.0)","Accept-Language":"en-US,en;q=0.9,nl;q=0.8"}
MATERIALS={
    "SS304":{"base_eurkg":2.8,"kind":"stainless"},
    "SS316L":{"base_eurkg":3.4,"kind":"stainless"},
    "1.4462_Duplex":{"base_eurkg":4.2,"kind":"stainless"},
    "SuperDuplex_2507":{"base_eurkg":5.4,"kind":"stainless"},
    "SS904L":{"base_eurkg":6.1,"kind":"stainless"},
    "Al_6082":{"base_eurkg":0.0,"kind":"aluminium"},
    "Extruded_Al_6060":{"base_eurkg":0.0,"kind":"aluminium"},
    "Cast_Aluminium":{"base_eurkg":0.0,"kind":"aluminium"},
    "S235JR_steel":{"base_eurkg":1.4,"kind":"other"},
    "S355J2_steel":{"base_eurkg":1.7,"kind":"other"},
}
OTK_KEY={"SS304":"304","SS316L":"316L","1.4462_Duplex":"2205","SuperDuplex_2507":"2507","SS904L":"904L"}
MACHINE_RATES={"CNC":85.0,"Laser":110.0,"Lassen":55.0,"Buigen":75.0,"Montage":40.0,"Casting":65.0}
LABOR=45.0; PROFIT=0.12; CONT=0.05

ROUTING_COLS=["Step","Proces","Qty_per_parent","Cycle_min","Setup_min","Attend_pct","kWh_pc","QA_min_pc","Scrap_pct","Parallel_machines","Batch_size","Queue_days"]
BOM_COLS=["Part","Qty","UnitPrice","Scrap_pct"]

# ---- Helpers / scrapers ----
eurton=lambda x:(x or 0)/1000.0
def parse_eur(s:str):
    s=(s or "").replace("\xa0"," ").strip()
    m=re.search(r"([0-9][0-9\.\,\s]*)",s); 
    if not m: return None
    x=m.group(1).replace(" ","")
    if "," in x and "." in x:
        last=max(x.rfind(","),x.rfind(".")); dec=x[last]; thou="." if dec=="," else ","
        x=x.replace(thou,"").replace(dec,".")
    elif "," in x:
        parts=x.split(","); x=x.replace(".", "").replace(",", ".") if len(parts[-1]) in (1,2) else x.replace(",","")
    elif x.count(".")>1: x=x.replace(".","")
    try: return float(x)
    except: return None

@st.cache_data(ttl=60*60*3)
def fetch_otk()->dict:
    url="https://www.outokumpu.com/en/surcharges"
    try:
        r=requests.get(url,headers=HEADERS,timeout=15); r.raise_for_status()
        text=re.sub(r"<[^>]+>"," ",r.text)
        out={}
        for k,pat in {"304":r"(?:304|1\.4301)[^\d€]{0,40}€\s*([0-9\.\,\s]+)",
                      "316L":r"(?:316L|1\.4404)[^\d€]{0,40}€\s*([0-9\.\,\s]+)",
                      "2205":r"(?:2205|1\.4462)[^\d€]{0,40}€\s*([0-9\.\,\s]+)",
                      "2507":r"(?:2507|1\.4410)[^\d€]{0,40}€\s*([0-9\.\,\s]+)",
                      "904L":r"(?:904L|1\.4539)[^\d€]{0,40}€\s*([0-9\.\,\s]+)"}.items():
            m=re.search(pat,text,re.I)
            if m:
                v=parse_eur(m.group(1))
                if v is not None: out[k]=v
        return out
    except Exception:
        return {}

@st.cache_data(ttl=30*60)
def fetch_lme_eur_ton():
    try:
        r=requests.get("https://tradingeconomics.com/commodity/aluminum",headers=HEADERS,timeout=12)
        r.raise_for_status()
        m=re.search(r'data-price="(\d{3,5}(?:\.\d{1,2})?)"',r.text)
        if not m: return None,"TE not found"
        usd=float(m.group(1)); fx=0.92
        return usd*fx,"TradingEconomics → FX 0.92"
    except Exception as e:
        return None,f"err:{e}"

# ---- Calculaties ----
def propagate_scrap(df: pd.DataFrame, Q: int):
    df=df.sort_values("Step").reset_index(drop=True).copy()
    need=float(Q); eff=[]
    for _,r in df[::-1].iterrows():
        good=max(1e-9,1.0-float(r.get("Scrap_pct",0.0)))
        need=need/good; eff.append(need)
    df["Eff_Input_Qty"]=list(reversed(eff))
    return df

def lean_costs(qty_in, batch_size, energy_kwh_pc, storage_days, storage_cost, km, eur_km, rework, rework_min, energy_eur, labor_rate):
    batches=int(np.ceil(qty_in/max(1,batch_size)))
    return storage_days*storage_cost*batches + km*eur_km + rework*qty_in*(rework_min/60.0)*labor_rate + qty_in*energy_kwh_pc*energy_eur

def cost_once(routing_df, bom_df, Q, netkg, mat_price, energy, labor_rate, machine_rates, storage_days, storage_cost, km, eur_km, rework, rework_min):
    mat_pc=netkg*mat_price; conv=0.0; lean=0.0
    if not routing_df.empty:
        r=propagate_scrap(routing_df,Q)
        for _,row in r.iterrows():
            proc=str(row.get("Proces","")); qty=float(row.get("Eff_Input_Qty",Q))
            par=max(1,int(row.get("Parallel_machines",1))); bs=max(1,int(row.get("Batch_size",50)))
            batches=int(np.ceil(qty/bs))
            setup=float(row.get("Setup_min",0.0))*batches; cycle=float(row.get("Cycle_min",0.0))*qty
            qa=float(row.get("QA_min_pc",0.0))*qty; att=float(row.get("Attend_pct",100))/100.0
            kwh=float(row.get("kWh_pc",0.0))*qty; mach_rate=float(machine_rates.get(proc, labor_rate))
            machine_min=(setup+cycle)/par; labor_min=(setup+cycle+qa)*att
            conv += (machine_min/60.0)*mach_rate + (labor_min/60.0)*labor_rate + kwh*energy
            lean += lean_costs(qty, bs, 0.0, storage_days, storage_cost, km, eur_km, rework, rework_min, energy, labor_rate)
    buy=0.0
    if not bom_df.empty:
        b=bom_df.copy(); b["Line"]=b["Qty"]*b["UnitPrice"]*(1.0+b.get("Scrap_pct",0.0)); buy=float(b["Line"].sum())*Q
    total=(mat_pc*Q+conv+lean+buy)/Q
    return {"mat_pc":mat_pc,"conv_total":conv,"lean_total":lean,"buy_total":buy,"total_pc":total}

def run_mc(routing_df,bom_df,Q,netkg,mat_mu,sd_mat,sd_cycle,sd_scrap,iters=1000,seed=123,
           energy=0.2,labor=LABOR,mrates=MACHINE_RATES,storage_days=0,storage_cost=0,km=0,eur_km=0,rework=0,rework_min=0):
    rng=np.random.default_rng(seed); out=[]; r0=pd.DataFrame(routing_df); b0=pd.DataFrame(bom_df)
    for _ in range(int(iters)):
        mat=max(0.01, rng.normal(mat_mu, sd_mat*mat_mu)); r=r0.copy()
        if not r.empty:
            if "Cycle_min" in r: r["Cycle_min"]=(r["Cycle_min"]*(1.0+rng.normal(0.0,sd_cycle,size=len(r)))).clip(lower=0.05)
            if "Scrap_pct" in r: r["Scrap_pct"]=(r["Scrap_pct"]+rng.normal(0.0,sd_scrap,size=len(r))).clip(0.0,0.35)
        rr=cost_once(r,b0,Q,netkg,mat,energy,labor,mrates,storage_days,storage_cost,km,eur_km,rework,rework_min)
        out.append(rr["total_pc"])
    return np.array(out)

def capacity_table(df: pd.DataFrame, Q: int, hours_day: float, cap_proc: dict) -> pd.DataFrame:
    if df is None or len(df)==0:
        return pd.DataFrame(columns=["Proces","Hours_need","Hours_cap","Util_pct","Batches","Setup_min","Cycle_min"])
    r=propagate_scrap(df.copy(),Q); rows=[]
    for _,row in r.iterrows():
        proc=str(row["Proces"]); qty=float(row.get("Eff_Input_Qty",Q))
        par=max(1,int(row.get("Parallel_machines",1))); bs=max(1,int(row.get("Batch_size",50)))
        batches=int(np.ceil(qty/bs)); setup=float(row.get("Setup_min",0.0))*batches; cycle=float(row.get("Cycle_min",0.0))*qty
        machine_min=(setup+cycle)/par; need_h=machine_min/60.0; cap_h=float(cap_proc.get(proc, hours_day))
        util=(need_h/max(cap_h,1e-6)) if cap_h>0 else np.nan
        rows.append([proc,need_h,cap_h,util,batches,setup,cycle])
    df=pd.DataFrame(rows,columns=["Proces","Hours_need","Hours_cap","Util_pct","Batches","Setup_min","Cycle_min"])
    df=df.groupby("Proces",as_index=False).sum(numeric_only=True); df["Util_pct"]=(df["Hours_need"]/df["Hours_cap"]).replace([np.inf,-np.inf],np.nan)
    return df.sort_values("Util_pct",ascending=False)

def build_powerbi_facts(routing_df,bom_df,Q,netkg,mat_price_eurkg,energy_eur_kwh,labor_rate,machine_rates,project,materiaal,price_source,mc_samples,res):
    now=pd.Timestamp.today().normalize()
    fact_run=pd.DataFrame([{"RunDate":now,"Project":project,"Q":Q,"Material":materiaal,"Material_EURkg":mat_price_eurkg,"PriceSource":price_source,
                            "UnitCost":res["total_pc"],"Mat_pc":res["mat_pc"],"Conv_total":res["conv_total"],
                            "Lean_total":res["lean_total"],"Buy_total":res["buy_total"]}])
    rows=[]; 
    if not routing_df.empty:
        r=propagate_scrap(routing_df,Q)
        for _,rw in r.iterrows():
            proc=str(rw.get("Proces","")); qty=float(rw.get("Eff_Input_Qty",Q)); par=max(1,int(rw.get("Parallel_machines",1)))
            bs=max(1,int(rw.get("Batch_size",50))); batches=int(np.ceil(qty/bs))
            setup=float(rw.get("Setup_min",0.0))*batches; cycle=float(rw.get("Cycle_min",0.0))*qty; qa=float(rw.get("QA_min_pc",0.0))*qty
            att=float(rw.get("Attend_pct",100))/100.0; kwh=float(rw.get("kWh_pc",0.0))*qty; mach=float(machine_rates.get(proc,labor_rate))
            machine_min=(setup+cycle)/par; labor_min=(setup+cycle+qa)*att
            rows.append({"RunDate":now,"Project":project,"Process":proc,"Step":rw.get("Step"),
                         "QtyInput":qty,"Batches":batches,"Setup_min":setup,"Cycle_min":cycle,"QA_min":qa,
                         "Attend_pct":att*100,"kWh_total":kwh,"Parallel_machines":par,
                         "Cost_Machine":(machine_min/60.0)*mach,"Cost_Labor":(labor_min/60.0)*labor_rate,
                         "Cost_Energy":kwh*energy_eur_kwh,"Cost_Lean":0.0})
    fact_routing=pd.DataFrame(rows); 
    fact_bom=pd.DataFrame()
    if not bom_df.empty:
        b=bom_df.copy(); b["Qty_Run"]=b["Qty"]*Q; b["Cost_Run"]=(b["Qty"]*b["UnitPrice"]*(1.0+b.get("Scrap_pct",0.0)))*Q
        b.insert(0,"RunDate",now); b.insert(1,"Project",project); b.rename(columns={"Qty":"Qty_per"},inplace=True)
        fact_bom=b[["RunDate","Project","Part","Qty_per","UnitPrice","Scrap_pct","Qty_Run","Cost_Run"]]
    fact_mc=pd.DataFrame()
    if mc_samples is not None and len(mc_samples)>0:
        fact_mc=pd.DataFrame({"RunDate":now,"Project":project,"ScenarioIdx":np.arange(1,len(mc_samples)+1),"UnitCost":mc_samples})
    dim_proc=pd.DataFrame([{"Process":p,"MachineRate_EURh":machine_rates.get(p,labor_rate)} for p in sorted(machine_rates.keys())])
    return {"FactRun":fact_run,"FactRouting":fact_routing,"FactBOM":fact_bom,"FactMC":fact_mc,"DimProcess":dim_proc}
