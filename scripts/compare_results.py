"""Compare a real Flux 2 run with the reference pipeline (test oracle).

Export the three lists from SharePoint (list → Export → Export to CSV) into one folder:
  Realizat_Lunar.csv, Erori_Import.csv, Analize_AI.csv
then run:
  python scripts/compare_results.py data/run_check/            # rates inferred from Realizat_Lunar
  python scripts/compare_results.py data/run_check/ --eur 5.34 --usd 4.87

The BNR rates used by the flow are read back from the EUR / USD rows of Realizat_Lunar
(Suma_RON / Suma), and the oracle is recomputed with them, so the comparison is exact.
Column headers may be display names (Cheie, Rulare_ID) or internal names (Title).
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reference_pipeline import compute, default_rates  # noqa: E402

TOL = 0.011  # RON / percentage points; SharePoint stores 2 decimals


def num(v) -> float:
    """Parse '12348', '12348.5', '12.348,50', '12,348.50', '' -> float."""
    s = str(v or "").strip().replace(" ", "").replace(" ", "")
    if not s:
        return 0.0
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    return float(s)


def when(v: str) -> datetime:
    """SharePoint CSV dates: '25.11.2026 16:20' (RO) or ISO; unknown -> minimal date."""
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M", "%m/%d/%Y %I:%M %p"):
        try:
            return datetime.strptime(v.strip(), fmt)
        except ValueError:
            pass
    return datetime.min


def boolean(v) -> bool:
    return str(v).strip().lower() in ("da", "yes", "true", "1", "adevărat")


def read(folder: Path, name: str, key_cols: tuple[str, ...]) -> list[dict]:
    p = folder / f"{name}.csv"
    if not p.exists():
        print(f"  (missing {p.name}, skipped)")
        return []
    with p.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:  # normalise the key column (display name or internal Title)
        r["_key"] = next((r[c] for c in key_cols + ("Title",) if c in r), "")
    return rows


class Report:
    def __init__(self):
        self.ok = self.bad = 0

    def check(self, label: str, got, exp, close: bool = False):
        good = abs(num(got) - num(exp)) <= TOL if close else got == exp
        self.ok += good
        self.bad += not good
        if not good:
            print(f"  ✗ {label}: got {got!r}, expected {exp!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--eur", type=float)
    ap.add_argument("--usd", type=float)
    args = ap.parse_args()

    real = read(args.folder, "Realizat_Lunar", ("Cheie",))
    erori = read(args.folder, "Erori_Import", ("Rulare_ID",))
    analize = read(args.folder, "Analize_AI", ("Cheie",))

    rates, rate_date = default_rates()
    for cur in ("EUR", "USD"):
        given = getattr(args, cur.lower())
        rows = [r for r in real if r.get("Moneda") == cur and num(r.get("Suma"))]
        if given:
            rates[cur] = given
        elif rows:  # rate actually used by the flow, rounded like BNR (4 decimals)
            rates[cur] = round(num(rows[0]["Suma_RON"]) / num(rows[0]["Suma"]), 4)
    exp = compute(rates, "din rulare")
    print(f"rates used: EUR {rates['EUR']}, USD {rates['USD']}\n")
    rep = Report()

    print("Realizat_Lunar")
    by_key = {r["_key"]: r for r in real if r.get("Luna") == exp["luna"]}
    rep.check("rows for the month", len(by_key), len(exp["realizat"]))
    for e in exp["realizat"]:
        g = by_key.get(e["cheie"])
        if not g:
            rep.check(f"{e['cheie']} present", False, True)
            continue
        rep.check(f"{e['cheie']} Suma_RON", g.get("Suma_RON"), e["suma_ron"], close=True)
        rep.check(f"{e['cheie']} Aprobat_RON", g.get("Aprobat_RON"), e["aprobat_ron"], close=True)
        rep.check(f"{e['cheie']} Maverick_RON", g.get("Maverick_RON"), e["maverick_ron"], close=True)
    if real:
        rep.check("no duplicate keys (upsert)",
                  len(by_key) == len([r for r in real if r.get("Luna") == exp["luna"]]), True)

    print("Erori_Import (latest run)")
    if erori:
        last = max(erori, key=lambda r: when(r.get("Data_Import", "")))["_key"]
        run = sorted((r for r in erori if r["_key"] == last), key=lambda r: num(r.get("Rand")))
        rep.check("error rows", len(run), len(exp["erori"]))
        for g, e in zip(run, exp["erori"]):
            rep.check(f"row {e['rand']} Tip_Eroare", g.get("Tip_Eroare"), e["tip"])
            rep.check(f"row {e['rand']} Cheie", g.get("Cheie", ""), e["cheie"])
            rep.check(f"row {e['rand']} Mesaj", g.get("Mesaj", "").strip(), e["mesaj"])

    print("Analize_AI")
    by_cc = {r.get("CentruCost"): r for r in analize if r.get("Luna") == exp["luna"]}
    if analize:
        rep.check("rows for the month (one per CC)", len(by_cc), len(exp["centre_cost"]))
    for c in exp["centre_cost"] if analize else []:
        g = by_cc.get(c["cc"])
        if not g:
            rep.check(f"{c['cc']} present", False, True)
            continue
        for col, key in (("Buget_RON", "buget_ron"), ("Angajat_RON", "angajat_ron"), ("Realizat_RON", "realizat_ron"),
                         ("Varianta_RON", "varianta_ron"), ("Varianta_Pct", "varianta_pct"),
                         ("Maverick_RON", "maverick_ron")):
            rep.check(f"{c['cc']} {col}", g.get(col), c[key], close=True)
        rep.check(f"{c['cc']} Alerta_Regula", g.get("Alerta_Regula"), c["alerta_regula"])
        if g.get("Status_Analiza") == "OK":
            rep.check(f"{c['cc']} Alerta_AI", g.get("Alerta_AI"), c["alerta_ai_asteptata"])
            rep.check(f"{c['cc']} Necesita_Revizuire", boolean(g.get("Necesita_Revizuire")),
                      c["necesita_revizuire_asteptat"])
        else:
            print(f"  ! {c['cc']}: Status_Analiza = {g.get('Status_Analiza')} ({g.get('Mesaj_Eroare', '')[:80]})")

    print(f"\n{rep.ok} checks OK, {rep.bad} differences")
    return 0 if rep.bad == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
