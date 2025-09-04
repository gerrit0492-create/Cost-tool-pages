# utils/perplexity_ingest.py
import json, os
from datetime import datetime
import pandas as pd

def _norm_date(s):
    try:
        return datetime.fromisoformat(str(s)[:10]).date().isoformat()
    except Exception:
        return datetime.today().date().isoformat()

def normalize(payload: str):
    """
    Neemt Perplexity JSON (als string) en geeft 2 DataFrames terug:
    - df_m (material_prices)
    - df_l (labor_rates)
    Lege lijsten -> lege DataFrames.
    """
    data = json.loads(payload)

    mats = data.get("material_prices", []) or []
    labs = data.get("labor_rates", []) or []

    # schoonmaken en standaard kolommen garanderen
    for m in mats:
        m["as_of_date"] = _norm_date(m.get("as_of_date", ""))
        m["price"] = float(m.get("price", 0) or 0)
        m.setdefault("material", "")
        m.setdefault("grade", "")
        m.setdefault("form", "")
        m.setdefault("region", "")
        m.setdefault("unit", "")
        m.setdefault("currency", "EUR")
        m.setdefault("source_url", "")
        m.setdefault("source_name", "")
        m.setdefault("forecast_3m", None)
        m.setdefault("forecast_6m", None)
        m.setdefault("notes", None)

    for l in labs:
        l["as_of_date"] = _norm_date(l.get("as_of_date", ""))
        l["rate_min"] = float(l.get("rate_min", 0) or 0)
        l["rate_max"] = float(l.get("rate_max", 0) or 0)
        l.setdefault("process", "")
        l.setdefault("country", "")
        l.setdefault("currency", "EUR")
        l.setdefault("source_url", "")
        l.setdefault("source_name", "")
        l.setdefault("basis", "")
        l.setdefault("notes", None)

    df_m = pd.DataFrame(mats, columns=[
        "material","grade","form","region","unit","price","currency",
        "as_of_date","source_url","source_name","forecast_3m","forecast_6m","notes"
    ])
    df_l = pd.DataFrame(labs, columns=[
        "process","country","rate_min","rate_max","currency","as_of_date",
        "source_url","source_name","basis","notes"
    ])
    return df_m, df_l

def save_append_csv(df: pd.DataFrame, path: str):
    """Voegt regels toe aan CSV (maakt map aan als nodig)."""
    if df.empty:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    header = not os.path.exists(path)
    df.to_csv(path, mode="a", header=header, index=False)

def dedupe_latest(df: pd.DataFrame, keys: list[str], date_col: str):
    """
    Houdt per sleutel-combinatie alleen de laatste regel (op datumkolom).
    Handig om dubbele entries uit Perplexity te verminderen.
    """
    if df.empty:
        return df
    d = df.copy()
    try:
        d[date_col] = pd.to_datetime(d[date_col])
        d = d.sort_values(date_col).groupby(keys, as_index=False).tail(1)
    except Exception:
        pass
    return d
