"""Reference implementation of Flux 2 — the test oracle.

Reads  data/input/realizat_2026-10.json, data/seed/{nomenclator,bugete,cereri_istorice_2026-10,config}.csv
Writes data/expected/expected_results.json

Usage:
  python scripts/reference_pipeline.py                 # fixed rates from data/expected/generation_meta.json
  python scripts/reference_pipeline.py --eur 5.35 --usd 4.88   # re-run with the rates the flow actually used
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ["luna", "centru_cost", "categorie", "suma", "moneda"]
CURRENCIES = ["RON", "EUR", "USD"]
ALERT_ORDER = ["Verde", "Galben", "Roșu"]


def read_csv(name):
    with (ROOT / "data" / "seed" / name).open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fmt_num(v):
    """Render numbers the way the error messages show them (no trailing .0)."""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def valid_month(l) -> bool:
    return (isinstance(l, str) and len(l) == 7 and l[4] == "-" and l[:4].isdigit() and l[5:].isdigit()
            and 1 <= int(l[5:]) <= 12)


def is_number(v) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return True
    try:
        float(str(v))
        return True
    except ValueError:
        return False


def validate(rows, coduri_cc, coduri_cat, rates):
    """Returns (valide, erori) exactly as the Apply-to-each in Flux 2 should."""
    seen: dict[str, int] = {}
    valide, erori = [], []
    cc_list = ", ".join(coduri_cc)
    cat_list = ", ".join(coduri_cat)

    for r in rows:
        rand = r.get("rand")
        luna, cc, cat, suma, moneda = (r.get(k) for k in REQUIRED)
        cheie = f"{luna}_{cc}_{cat}" if valid_month(luna) and cc and cat else ""
        ref = f"Rândul {rand} ({cheie})" if cheie else f"Rândul {rand}"

        def err(tip, mesaj):
            erori.append({"rand": rand, "cheie": cheie, "tip": tip, "mesaj": mesaj})

        missing = [k for k in REQUIRED if r.get(k) in (None, "")]
        if missing:
            err("Câmp lipsă", f"{ref}: lipsesc câmpurile obligatorii {', '.join(missing)}.")
            continue
        if not valid_month(luna):
            err("Format lună", f"{ref}: luna „{luna}” are format greșit; formatul corect este AAAA-LL (ex. 2026-10).")
            continue
        if not is_number(suma):
            err("Tip invalid", f"{ref}: suma „{suma}” nu este un număr.")
            continue
        if float(suma) <= 0:
            err("Valoare în afara domeniului",
                f"{ref}: suma {fmt_num(suma)} nu este validă; se acceptă doar valori mai mari decât 0.")
            continue
        if moneda not in CURRENCIES:
            err("Valoare în afara domeniului",
                f"{ref}: moneda „{moneda}” nu este acceptată; valori permise: {', '.join(CURRENCIES)}.")
            continue
        if cc not in coduri_cc:
            err("Cod necunoscut", f"{ref}: centrul de cost „{cc}” nu există în nomenclator. Coduri valide: {cc_list}.")
            continue
        if cat not in coduri_cat:
            err("Cod necunoscut", f"{ref}: categoria „{cat}” nu există în nomenclator. Coduri valide: {cat_list}.")
            continue
        if cheie in seen:
            err("Duplicat", f"{ref}: înregistrare duplicat — cheia a apărut deja la rândul {seen[cheie]}; rândul a fost ignorat.")
            continue
        seen[cheie] = rand
        suma_f = float(suma)
        valide.append({
            "rand": rand, "cheie": cheie, "luna": luna, "cc": cc, "cat": cat, "suma": suma_f, "moneda": moneda,
            "suma_ron": round(suma_f * rates[moneda], 2), "nr_documente": r.get("nr_documente"),
        })
    return valide, erori


def alert_rule(pct: float, prag: float) -> str:
    a = abs(pct)
    if a <= 5:
        return "Verde"
    if a <= prag:
        return "Galben"
    return "Roșu"


def default_rates() -> tuple[dict, str]:
    meta = json.loads((ROOT / "data" / "expected" / "generation_meta.json").read_text(encoding="utf-8"))
    return dict(meta["rates"]), meta["rate_date"]


def compute(rates: dict, rate_date: str) -> dict:
    """Runs the whole Flux 2 logic in memory and returns the expected-results object."""
    payload = json.loads((ROOT / "data" / "input" / "realizat_2026-10.json").read_text(encoding="utf-8"))
    nomen = read_csv("nomenclator.csv")
    coduri_cc = [n["Title"] for n in nomen if n["Tip"] == "CC"]
    coduri_cat = [n["Title"] for n in nomen if n["Tip"] == "CAT"]
    cfg = {c["Title"]: c["Valoare"] for c in read_csv("config.csv")}
    prag = float(cfg["prag_alerta_pct"])

    rows = payload["inregistrari"]
    valide, erori = validate(rows, coduri_cc, coduri_cat, rates)

    # approved amount per key (Aprobată or Exportată), from Flux 1 history
    aprobat: dict[str, float] = {}
    for c in read_csv("cereri_istorice_2026-10.csv"):
        if c["Status"] in ("Aprobată", "Exportată"):
            k = f'{c["Luna_Buget"]}_{c["CentruCost"]}_{c["Categorie"]}'
            aprobat[k] = round(aprobat.get(k, 0.0) + float(c["Valoare_RON"]), 2)

    realizat = []
    for v in valide:
        a = aprobat.get(v["cheie"], 0.0)
        realizat.append({**v, "aprobat_ron": a, "maverick_ron": round(max(0.0, v["suma_ron"] - a), 2)})
    real_by_key = {r["cheie"]: r for r in realizat}

    bugete = [b for b in read_csv("bugete.csv") if b["Luna"] == payload["luna"]]
    cc_table = []
    for cc in coduri_cc:
        rows_cc = [b for b in bugete if b["CentruCost"] == cc]
        buget = sum(float(b["Buget_RON"]) for b in rows_cc)
        angajat = round(sum(float(b["Angajat_RON"]) for b in rows_cc), 2)
        real = round(sum(real_by_key[b["Title"]]["suma_ron"] for b in rows_cc if b["Title"] in real_by_key), 2)
        mav = round(sum(real_by_key[b["Title"]]["maverick_ron"] for b in rows_cc if b["Title"] in real_by_key), 2)
        var = round(real - buget, 2)
        pct = round(var * 100 / buget, 2)
        rule = alert_rule(pct, prag)
        ai_min = rule if mav <= 0 else ALERT_ORDER[max(ALERT_ORDER.index(rule), 1)]
        categorii = []
        for b in rows_cc:
            r = real_by_key.get(b["Title"])
            categorii.append({
                "categorie": b["Categorie"], "buget": float(b["Buget_RON"]), "angajat": float(b["Angajat_RON"]),
                "realizat": r["suma_ron"] if r else 0.0, "maverick": r["maverick_ron"] if r else 0.0,
            })
        cc_table.append({
            "cc": cc, "luna": payload["luna"], "buget_ron": buget, "angajat_ron": angajat, "realizat_ron": real,
            "varianta_ron": var, "varianta_pct": pct, "maverick_ron": mav, "alerta_regula": rule,
            "alerta_ai_asteptata": ai_min, "necesita_revizuire_asteptat": ai_min != rule, "categorii": categorii,
        })

    tipuri = {}
    for e in erori:
        tipuri[e["tip"]] = tipuri.get(e["tip"], 0) + 1
    result = {
        "fisier": "realizat_2026-10.json",
        "luna": payload["luna"],
        "cursuri": {"data": rate_date, **rates},
        "sumar": {
            "total": len(rows), "valide": len(valide), "invalide": len(erori) - tipuri.get("Duplicat", 0),
            "duplicate": tipuri.get("Duplicat", 0), "erori_pe_tip": tipuri,
        },
        "erori": erori,
        "realizat": realizat,
        "maverick": [{"cheie": r["cheie"], "maverick_ron": r["maverick_ron"]} for r in realizat if r["maverick_ron"] > 0],
        "centre_cost": cc_table,
    }
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eur", type=float)
    ap.add_argument("--usd", type=float)
    args = ap.parse_args()

    rates, rate_date = default_rates()
    if args.eur:
        rates["EUR"] = args.eur
    if args.usd:
        rates["USD"] = args.usd
    result = compute(rates, rate_date)
    erori = result["erori"]
    cc_table = result["centre_cost"]

    out = ROOT / "data" / "expected" / "expected_results.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    s = result["sumar"]
    print(f"rows {s['total']}: valid {s['valide']}, invalid {s['invalide']}, duplicate {s['duplicate']}")
    for e in erori:
        print("  ERR", e["tip"], "|", e["mesaj"])
    print("maverick:", result["maverick"])
    print(f"{'CC':<4}{'buget':>10}{'angajat':>11}{'realizat':>11}{'var%':>8}  regula  AI-min   revizuire")
    for c in cc_table:
        print(f"{c['cc']:<4}{c['buget_ron']:>10.0f}{c['angajat_ron']:>11.0f}{c['realizat_ron']:>11.0f}"
              f"{c['varianta_pct']:>8.2f}  {c['alerta_regula']:<7} {c['alerta_ai_asteptata']:<8} {c['necesita_revizuire_asteptat']}")


if __name__ == "__main__":
    main()
