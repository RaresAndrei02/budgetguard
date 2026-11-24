"""Fetch the BNR daily FX XML, save it to samples/ and print the rates used by BudgetGuard."""
import pathlib
import sys
import xml.etree.ElementTree as ET

import requests

# www.bnr.ro/nbrfxrates.xml now redirects to the HTML homepage (checked 2026-11-18).
URL = "https://curs.bnr.ro/nbrfxrates.xml"
ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    resp = requests.get(URL, timeout=30)
    print(f"HTTP {resp.status_code}, {len(resp.content)} bytes")
    resp.raise_for_status()
    out = ROOT / "samples" / "bnr_nbrfxrates.xml"
    out.write_bytes(resp.content)
    print(f"Saved {out.relative_to(ROOT)}")

    root = ET.fromstring(resp.content)
    # Ignore namespaces, mirroring the local-name() XPath used in Power Automate.
    cube = next(e for e in root.iter() if e.tag.endswith("Cube"))
    print(f"Cube date: {cube.get('date')}")
    for e in root.iter():
        if e.tag.endswith("Rate") and e.get("currency") in ("EUR", "USD"):
            print(f"{e.get('currency')} = {e.text} (multiplier={e.get('multiplier', '1')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
