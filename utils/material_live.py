# utils/material_live.py
# Eenvoudige live-fetchers voor materiaalprijzen in €/kg.
# Vereist: requests, beautifulsoup4

from __future__ import annotations
import datetime as dt
from typing import Optional, Dict, Any

import requests
from bs4 import BeautifulSoup

UserAgent = "Mozilla/5.0 (compatible; CostTool/1.0; +https://example.local)"

def _now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")

def fetch_duplex_14462_bar_eu() -> Optional[Dict[str, Any]]:
    """
    Demo-scraper: haalt een indicatieve prijs voor 1.4462 (duplex) bar in EU.
    Pas de URL/selectors aan naar jouw echte bron (leverancier/LME/portaal).
    Retourneert een dict klaar voor material_prices.csv of None bij mislukking.
    """
    url = "https://voorbeeld.local/duplex-bar"  # <-- vervang door echte bron-URL
    try:
        resp = requests.get(url, headers={"User-Agent": UserAgent}, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Voorbeeld selector (pas aan!):
        # <span id="price-eurkg">4.20</span>
        node = soup.select_one("#price-eurkg")
        price = float(node.get_text(strip=True)) if node and node.get_text(strip=True) else None
        if not price:
            return None

        return {
            "material": "stainless steel",
            "grade": "1.4462",
            "form": "bar",
            "region": "EU",
            "unit": "€/kg",
            "price": price,
            "currency": "EUR",
            "as_of_date": _now_iso().split("T")[0],
            "source_url": url,
            "source_name": "Live scraper (duplex bar)",
            "forecast_3m": round(price * 1.03, 2),
            "forecast_6m": round(price * 1.07, 2),
            "notes": "Automatisch opgehaald; vervang bron+selector wanneer beschikbaar."
        }
    except Exception:
        return None

def fetch_generic_grade(grade: str, form: str = "bar", region: str = "EU") -> Optional[Dict[str, Any]]:
    """
    Router voor verschillende grades. Voeg hier case-blokken toe per materiaal.
    """
    g = (grade or "").strip().lower()
    f = (form or "").strip().lower()
    r = (region or "").strip().upper()

    if g in {"1.4462", "duplex 2205", "s32205", "s31803"} and f == "bar" and r == "EU":
        return fetch_duplex_14462_bar_eu()

    # TODO: meer fetchers toevoegen (316L sheet, 304 bar, C45 bar, etc.)
    return None
