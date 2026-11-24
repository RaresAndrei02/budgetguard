"""Probe the ANAF VAT-payer REST API (v9) and save the raw response to samples/.

Usage: python scripts/check_anaf.py [CUI ...]
Default CUIs: 3 well-known companies + 1 that should not exist.
"""
import datetime as dt
import json
import pathlib
import sys

import requests

URL = "https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva"
DEFAULT_CUIS = [2816464, 14399840, 9010105, 99999999]  # Dedeman, eMAG (Dante Intl.), Orange RO, nonexistent
ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    cuis = [int(c) for c in sys.argv[1:]] or DEFAULT_CUIS
    today = dt.date.today().isoformat()
    body = [{"cui": c, "data": today} for c in cuis]
    resp = requests.post(URL, json=body, headers={"Content-Type": "application/json"}, timeout=30)
    print(f"HTTP {resp.status_code}, {len(resp.content)} bytes")
    resp.raise_for_status()
    data = resp.json()

    out = ROOT / "samples" / "anaf_v9_response.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {out.relative_to(ROOT)}")

    for f in data.get("found", []):
        g = f.get("date_generale", {})
        print(
            f"FOUND {g.get('cui')}: {g.get('denumire')} | "
            f"scpTVA={f.get('inregistrare_scop_Tva', {}).get('scpTVA')} | "
            f"statusInactivi={f.get('stare_inactiv', {}).get('statusInactivi')}"
        )
    print(f"NOT FOUND: {data.get('notFound')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
