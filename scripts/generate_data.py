"""Generate all BudgetGuard test data deterministically (fixed seed).

Outputs:
  data/seed/nomenclator.csv, config.csv, bugete.csv, cereri_istorice_2026-10.csv
  data/input/realizat_2026-10.json (+ .xlsx, sheet "Realizat", table "tblRealizat")

Demo scenario, evaluated per cost centre for 2026-10:
  MKT  ~ +12% over budget  -> Rosu   (driven by MKT/MKT +18%, unplanned campaign)
  OPS  ~ +7%               -> Galben (OPS/SRV +8%)
  IT   ~ -4%               -> Verde  (IT/HW saves 25%, offset by SW/SRV)
  HR   ~ +1%               -> Verde by rule, but HR/TRN has ~12,350 RON spent with no approved request (maverick)
  SAL  ~ 0%                -> Verde
Approved requests cover every realised key except HR/TRN, so maverick appears only there.
"""
from __future__ import annotations

import csv
import json
import math
import random
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED_DIR = ROOT / "data" / "seed"
INPUT_DIR = ROOT / "data" / "input"
RNG = random.Random(20261103)

LUNA = "2026-10"
MONTHS = ["2026-10", "2026-11", "2026-12", "2027-01", "2027-02", "2027-03"]
SEASON = {"2026-10": 1.00, "2026-11": 1.05, "2026-12": 1.15, "2027-01": 0.90, "2027-02": 0.95, "2027-03": 1.00}

CC = {"IT": "Tehnologie", "MKT": "Marketing", "OPS": "Operațiuni", "HR": "Resurse umane", "SAL": "Vânzări"}
CAT = {"HW": "Hardware", "SW": "Software/SaaS", "SRV": "Servicii", "TRN": "Training", "MKT": "Marketing", "BIR": "Birotică"}

# Monthly base budget (RON) per cost centre / category (budgeted combinations).
BUDGET = {
    ("IT", "HW"): 60000, ("IT", "SW"): 45000, ("IT", "SRV"): 30000, ("IT", "TRN"): 10000,
    ("MKT", "MKT"): 80000, ("MKT", "SRV"): 25000, ("MKT", "SW"): 15000, ("MKT", "TRN"): 8000,
    ("OPS", "HW"): 35000, ("OPS", "SRV"): 50000, ("OPS", "BIR"): 12000, ("OPS", "TRN"): 9000,
    ("HR", "TRN"): 12000, ("HR", "SRV"): 20000, ("HR", "SW"): 12000, ("HR", "BIR"): 6000,
    ("SAL", "MKT"): 30000, ("SAL", "TRN"): 15000, ("SAL", "BIR"): 8000, ("SAL", "SW"): 18000,
}
# October actuals as relative deviation from budget (per key).
ACTUAL_DELTA = {
    ("IT", "HW"): -0.25, ("IT", "SW"): 0.15, ("IT", "SRV"): 0.08, ("IT", "TRN"): 0.05,
    ("MKT", "MKT"): 0.18, ("MKT", "SRV"): 0.05, ("MKT", "SW"): 0.00, ("MKT", "TRN"): -0.05,
    ("OPS", "HW"): 0.07, ("OPS", "SRV"): 0.08, ("OPS", "BIR"): 0.06, ("OPS", "TRN"): 0.05,
    ("HR", "TRN"): 0.029, ("HR", "SRV"): 0.03, ("HR", "SW"): -0.042, ("HR", "BIR"): 0.025,
    ("SAL", "MKT"): 0.02, ("SAL", "TRN"): -0.04, ("SAL", "BIR"): 0.00, ("SAL", "SW"): 0.01,
}
FOREIGN = {("MKT", "SW"): "EUR", ("SAL", "SW"): "EUR", ("OPS", "HW"): "EUR", ("IT", "SRV"): "USD"}
MAVERICK_KEYS = {("HR", "TRN")}  # realised without any approved request
SPLIT_KEYS = {("IT", "HW"), ("MKT", "MKT"), ("OPS", "SRV")}  # two approved requests each
EXPORTED_KEYS = {("IT", "SW"), ("SAL", "MKT"), ("OPS", "BIR")}  # already exported -> status Exportata

# Real companies verified via ANAF on 2026-11-18 (samples/anaf_v9_response.json).
SUPPLIERS = {
    "HW": ("14399840", "DANTE INTERNATIONAL SA"),
    "BIR": ("2816464", "DEDEMAN SRL"),
    "SW": ("9010105", "ORANGE ROMANIA SA"),
    "SRV": ("9010105", "ORANGE ROMANIA SA"),
    "TRN": ("14399840", "DANTE INTERNATIONAL SA"),
    "MKT": ("9010105", "ORANGE ROMANIA SA"),
}
TITLES = {
    "HW": "Laptopuri și periferice", "SW": "Abonamente software", "SRV": "Servicii externe",
    "TRN": "Curs de formare", "MKT": "Campanie de promovare", "BIR": "Consumabile birou",
}

PLACEHOLDER_EMAIL = "COMPLETEAZA_EMAIL_ASE"


def bnr_rates() -> tuple[str, dict]:
    """Rates from the real BNR sample saved in phase 1 (fixed, so data stays deterministic)."""
    root = ET.parse(ROOT / "samples" / "bnr_nbrfxrates.xml").getroot()
    cube = next(e for e in root.iter() if e.tag.endswith("Cube"))
    rates = {e.get("currency"): float(e.text) for e in root.iter() if e.tag.endswith("Rate")}
    return cube.get("date"), {"RON": 1.0, "EUR": rates["EUR"], "USD": rates["USD"]}


def write_csv(path: Path, header: list[str], rows: list[list]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:  # BOM so Excel opens diacritics correctly
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def iso(d: date | datetime) -> str:
    if isinstance(d, datetime):
        return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{d.isoformat()}T00:00:00Z"


def main():
    rate_date, RATES = bnr_rates()

    # ---------------------------------------------------------------- nomenclator
    nomen = [[k, "CC", v] for k, v in CC.items()] + [[k, "CAT", v] for k, v in CAT.items()]
    write_csv(SEED_DIR / "nomenclator.csv", ["Title", "Tip", "Denumire"], nomen)

    # ---------------------------------------------------------------- config
    config = [
        ["mod_demo", "false"],
        ["aprobator_1", PLACEHOLDER_EMAIL],
        ["aprobator_2", PLACEHOLDER_EMAIL],
        ["aprobator_3", PLACEHOLDER_EMAIL],
        ["aprobator_cfo", PLACEHOLDER_EMAIL],
        ["email_bcc", "bcc@example.com"],
        ["email_echipa", PLACEHOLDER_EMAIL],
        ["prag_cfo_ron", "100000"],
        ["prag_capex_ron", "2500"],
        ["prag_alerta_pct", "10"],
        ["valoare_max_ron", "500000"],
        ["zile_min_avans", "5"],
        ["teams_team_id", "COMPLETEAZA_IN_FAZA_4"],
        ["teams_channel_id", "COMPLETEAZA_IN_FAZA_4"],
        ["curs_fallback_EUR", f"{RATES['EUR']}"],
        ["curs_fallback_USD", f"{RATES['USD']}"],
    ]
    write_csv(SEED_DIR / "config.csv", ["Title", "Valoare"], config)

    # ---------------------------------------------------------------- October actuals (RON targets)
    actual_ron_target = {k: round(BUDGET[k] * (1 + ACTUAL_DELTA[k]), 2) for k in BUDGET}
    actual_rows = {}
    for k, target in actual_ron_target.items():
        cur = FOREIGN.get(k, "RON")
        amount = round(target / RATES[cur], 2) if cur != "RON" else target
        actual_rows[k] = {"suma": amount, "moneda": cur, "suma_ron": round(amount * RATES[cur], 2)}

    # ---------------------------------------------------------------- historical approved requests (October)
    cereri = []
    for k in BUDGET:
        if k in MAVERICK_KEYS:
            continue
        need = actual_rows[k]["suma_ron"]
        total = math.ceil(need * RNG.uniform(1.0, 1.06) / 50) * 50  # approved >= realised -> no maverick
        parts = [round(total * 0.6 / 50) * 50] if k in SPLIT_KEYS else []
        parts.append(total - sum(parts))
        for p in parts:
            cereri.append((k, p))
    RNG.shuffle(cereri)

    angajat = {k: 0.0 for k in BUDGET}
    cereri_rows = []
    for idx, (k, value_ron) in enumerate(sorted(cereri, key=lambda c: RNG.random()), start=1):
        cc, cat = k
        cur = "EUR" if (idx % 7 == 0) else "RON"
        rate = RATES[cur]
        valoare = math.ceil(value_ron / rate * 100) / 100 if cur != "RON" else float(value_ron)
        valoare_ron = round(valoare * rate, 2)
        before = angajat[k]
        angajat[k] = round(before + valoare_ron, 2)
        peste = angajat[k] > BUDGET[k]
        d_cerere = datetime(2026, 9, 15, 8, 0, tzinfo=timezone.utc) + timedelta(days=RNG.randint(0, 22), hours=RNG.randint(0, 8))
        # respect V4 (needed date >= request date + 5 days) and stay inside the budget month
        d_necesar = max(date(2026, 10, RNG.randint(5, 28)), d_cerere.date() + timedelta(days=5))
        d_necesar = min(d_necesar, date(2026, 10, 31))
        d_final = d_cerere + timedelta(days=RNG.randint(1, 4), hours=RNG.randint(1, 6))
        tip = "CAPEX" if cat == "HW" and valoare_ron >= 2500 else "OPEX"
        cui, furnizor = SUPPLIERS[cat]
        avert = "Valoarea depășește bugetul rămas; aprobare CFO solicitată." if peste else ""
        pasi = ["manager.cc", "controlling", "director.financiar"] + (["cfo"] if peste else [])
        aprobari = " | ".join(f"Pas {i}: {p}@vestra-retail.example – Aprobat" for i, p in enumerate(pasi, 1))
        status = "Exportată" if k in EXPORTED_KEYS else "Aprobată"
        cereri_rows.append({
            "Title": None, "TitluCerere": f"{TITLES[cat]} – {CC[cc]}", "CentruCost": cc, "Categorie": cat,
            "Luna_Buget": LUNA, "CUI": cui, "Furnizor_ANAF": furnizor, "Platitor_TVA": True,
            "Valoare": valoare, "Moneda": cur, "Curs_BNR": rate, "Valoare_RON": valoare_ron, "Tip": tip,
            "Data_Necesara": iso(d_necesar), "Recurenta": cat in ("SW", "SRV"), "Urgenta": RNG.randint(1, 5),
            "Justificare": f"Necesar operațional {CC[cc].lower()} – {CAT[cat].lower()}, octombrie 2026.",
            "Peste_Buget": peste, "Avertismente": avert, "Status": status,
            "Solicitant_Email": f"solicitant.{cc.lower()}@vestra-retail.example",
            "Data_Cerere": iso(d_cerere), "Aprobari": aprobari, "Motiv_Respingere": "",
            "Data_Finalizare": iso(d_final), "_sort": d_cerere,
        })
    cereri_rows.sort(key=lambda r: r["_sort"])
    for i, r in enumerate(cereri_rows, start=1):
        r["Title"] = f"PR-2026-{i:04d}"
        del r["_sort"]
    cols = list(cereri_rows[0].keys())
    write_csv(SEED_DIR / "cereri_istorice_2026-10.csv", cols,
              [[str(r[c]).lower() if isinstance(r[c], bool) else r[c] for c in cols] for r in cereri_rows])

    # ---------------------------------------------------------------- budgets (6 months x 20 keys)
    bug_rows = []
    for m in MONTHS:
        for (cc, cat), base in BUDGET.items():
            buget = base if m == LUNA else round(base * SEASON[m] / 100) * 100
            ang = angajat[(cc, cat)] if m == LUNA else 0.0
            bug_rows.append([f"{m}_{cc}_{cat}", m, cc, cat, buget, ang, 0, round(buget - ang, 2)])
    write_csv(SEED_DIR / "bugete.csv",
              ["Title", "Luna", "CentruCost", "Categorie", "Buget_RON", "Angajat_RON", "Realizat_RON", "Ramas_RON"],
              bug_rows)

    # ---------------------------------------------------------------- import file (24 rows)
    valid = [k for k in BUDGET if k != ("IT", "SW")]
    RNG.shuffle(valid)
    valid = [("IT", "SW")] + valid  # row 1 = IT/SW so the duplicate message matches the error catalogue in docs/expresii.md
    special = {
        9: {"luna": LUNA, "centru_cost": "LOG", "categorie": "SRV", "suma": 8700.00, "moneda": "RON", "nr_documente": 3},
        14: {"luna": LUNA, "centru_cost": "OPS", "categorie": "BIR", "suma": -1500, "moneda": "RON", "nr_documente": 1},
        17: {"luna": "10/2026", "centru_cost": "SAL", "categorie": "BIR", "suma": 2300.00, "moneda": "RON", "nr_documente": 2},
        22: {"luna": LUNA, "centru_cost": "IT", "categorie": "SW", "suma": 19900.00, "moneda": "RON", "nr_documente": 4},
    }
    inreg, it = [], iter(valid)
    for rand in range(1, 25):
        if rand in special:
            row = special[rand]
        else:
            cc, cat = next(it)
            a = actual_rows[(cc, cat)]
            row = {"luna": LUNA, "centru_cost": cc, "categorie": cat, "suma": a["suma"], "moneda": a["moneda"],
                   "nr_documente": RNG.randint(1, 12)}
        inreg.append({"rand": rand, **row})
    payload = {
        "sursa": "ERP Vestra – export cheltuieli realizate",
        "luna": LUNA,
        "generat_la": "2026-11-03T08:15:00",
        "inregistrari": inreg,
    }
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    (INPUT_DIR / "realizat_2026-10.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_xlsx(INPUT_DIR / "realizat_2026-10.xlsx", inreg)

    # meta used by the reference pipeline
    meta = {"rate_date": rate_date, "rates": RATES, "luna": LUNA}
    (ROOT / "data" / "expected").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "expected" / "generation_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"nomenclator: {len(nomen)}, config: {len(config)}, bugete: {len(bug_rows)}, "
          f"cereri istorice: {len(cereri_rows)}, import rows: {len(inreg)} (rates {rate_date}: {RATES})")


def write_xlsx(path: Path, rows: list[dict]):
    from openpyxl import Workbook
    from openpyxl.worksheet.table import Table, TableStyleInfo

    wb = Workbook()
    ws = wb.active
    ws.title = "Realizat"
    header = ["rand", "luna", "centru_cost", "categorie", "suma", "moneda", "nr_documente"]
    ws.append(header)
    for r in rows:
        ws.append([r[h] for h in header])
    ref = f"A1:G{len(rows) + 1}"
    t = Table(displayName="tblRealizat", ref=ref)
    t.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(t)
    for col, width in zip("ABCDEFG", (7, 10, 13, 11, 12, 9, 14)):
        ws.column_dimensions[col].width = width
    wb.save(path)


if __name__ == "__main__":
    main()
