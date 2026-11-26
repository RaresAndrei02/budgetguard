"""Render the BudgetGuard report and generate the matching Power Automate expressions.

One source of truth: report/template.html (page) + report/fragments/*.html (repeated rows).
Each {{token}} in a fragment has two definitions below: a Python one (used for preview.html)
and a Power Automate one (used to build the Select expressions). That keeps the real email
and the preview identical by construction.

Usage:
    python report/render_preview.py            # -> report/preview.html (from expected_results + ai/samples)
    python report/render_preview.py --flow     # -> docs/raport_expresii.md (expressions to paste in the flow)
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "report"
FRAG = REPORT / "fragments"
TOKEN = re.compile(r"\{\{(\w+)\}\}")
PA_EXPR_LIMIT = 8192  # Logic Apps limit for a single expression

# ---------------------------------------------------------------- shared helpers

ALERT_BG = {"Roșu": "#fee4e2", "Galben": "#fef3c7", "Verde": "#dcfce7"}
ALERT_FG = {"Roșu": "#b42318", "Galben": "#92400e", "Verde": "#166534"}
GREY_BG, GREY_FG = "#f3f4f6", "#6b7280"
RED, GREEN, MUTED = "#b42318", "#15803d", "#9ca3af"

BADGE_REVIEW_ROW = '<div style="font-size:11px;color:#b45309;font-weight:600;margin-top:3px">⚠ necesită revizuire</div>'
BADGE_FAIL_ROW = '<div style="font-size:11px;color:#6b7280;margin-top:3px">AI indisponibil</div>'
BADGE_REVIEW_BLOC = ' <span style="font-size:11px;color:#b45309;font-weight:600;margin-left:6px">⚠ necesită revizuire (regula: {r})</span>'
BADGE_FAIL_BLOC = ' <span style="font-size:11px;color:#6b7280;margin-left:6px">analiza AI a eșuat</span>'
ACTIUNE_HTML = '<div style="font-size:13px;margin-top:6px;color:#374151"><b>Acțiune recomandată:</b> {a}</div>'
EMPTY_MAV = '<tr><td colspan="4" style="padding:6px 8px;border-top:1px solid #e5e7eb;color:#6b7280">Nicio cheltuială fără cerere aprobată.</td></tr>'
EMPTY_ERR = '<tr><td colspan="3" style="padding:6px 8px;border-top:1px solid #e5e7eb;color:#6b7280">Nicio înregistrare respinsă.</td></tr>'


def fmt(x: float, decimals: int) -> str:
    """.NET formatNumber(x, 'N<d>', 'ro-RO'): '.' thousands, ',' decimals, half away from zero."""
    q = Decimal(str(x)).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    sign = "-" if q < 0 else ""
    whole, _, frac = f"{abs(q):f}".partition(".")
    whole = f"{int(whole):,}".replace(",", ".")
    return sign + whole + ("," + frac if decimals else "")


def signed(x: float, decimals: int) -> str:
    return ("+" if x > 0 else "") + fmt(x, decimals)


def pa_str(s: str) -> str:
    """Quote a literal for a Power Automate expression."""
    return "'" + s.replace("'", "''") + "'"


def pa_alert(x: str, table: dict, default: str) -> str:
    return (f"if(equals({x}, 'Roșu'), '{table['Roșu']}', if(equals({x}, 'Galben'), '{table['Galben']}', "
            f"if(equals({x}, 'Verde'), '{table['Verde']}', '{default}')))")


def pa_num(x: str, decimals: int) -> str:
    return f"formatNumber(float({x}), 'N{decimals}', 'ro-RO')"


def pa_signed(x: str, decimals: int) -> str:
    return f"concat(if(greater(float({x}), 0), '+', ''), {pa_num(x, decimals)})"


# ---------------------------------------------------------------- token definitions
# Items of varRezCC (built by Rez_CC in the flow): cc, buget, angajat, realizat, varianta_ron,
# varianta_pct, maverick, alerta_regula, alerta_ai, status, comentariu, actiune (all strings).

def _i(k: str) -> str:
    return f"item()?['{k}']"


REVIEW_COND = f"and(equals({_i('status')}, 'OK'), not(equals({_i('alerta_ai')}, {_i('alerta_regula')})))"

CC_TOKENS = {
    "cc": (lambda c: c["cc"], _i("cc")),
    "buget": (lambda c: fmt(c["buget"], 0), pa_num(_i("buget"), 0)),
    "realizat": (lambda c: fmt(c["realizat"], 0), pa_num(_i("realizat"), 0)),
    "var_ron": (lambda c: signed(c["varianta_ron"], 0), pa_signed(_i("varianta_ron"), 0)),
    "var_pct": (lambda c: signed(c["varianta_pct"], 2) + "%", f"concat({pa_signed(_i('varianta_pct'), 2)}, '%')"),
    "var_culoare": (lambda c: RED if c["varianta_ron"] > 0 else GREEN,
                    f"if(greater(float({_i('varianta_ron')}), 0), '{RED}', '{GREEN}')"),
    "maverick": (lambda c: fmt(c["maverick"], 0), pa_num(_i("maverick"), 0)),
    "mav_culoare": (lambda c: RED if c["maverick"] > 0 else MUTED,
                    f"if(greater(float({_i('maverick')}), 0), '{RED}', '{MUTED}')"),
    "alerta_regula": (lambda c: c["alerta_regula"], _i("alerta_regula")),
    "regula_fundal": (lambda c: ALERT_BG.get(c["alerta_regula"], GREY_BG), pa_alert(_i("alerta_regula"), ALERT_BG, GREY_BG)),
    "regula_text": (lambda c: ALERT_FG.get(c["alerta_regula"], GREY_FG), pa_alert(_i("alerta_regula"), ALERT_FG, GREY_FG)),
    "alerta_ai": (lambda c: c["alerta_ai"], _i("alerta_ai")),
    "ai_fundal": (lambda c: ALERT_BG.get(c["alerta_ai"], GREY_BG), pa_alert(_i("alerta_ai"), ALERT_BG, GREY_BG)),
    "ai_text": (lambda c: ALERT_FG.get(c["alerta_ai"], GREY_FG), pa_alert(_i("alerta_ai"), ALERT_FG, GREY_FG)),
    "marcaj_rand": (
        lambda c: BADGE_REVIEW_ROW if c["status"] == "OK" and c["alerta_ai"] != c["alerta_regula"]
        else ("" if c["status"] == "OK" else BADGE_FAIL_ROW),
        f"if({REVIEW_COND}, {pa_str(BADGE_REVIEW_ROW)}, if(equals({_i('status')}, 'OK'), '', {pa_str(BADGE_FAIL_ROW)}))"),
    "marcaj_bloc": (
        lambda c: BADGE_REVIEW_BLOC.format(r=c["alerta_regula"]) if c["status"] == "OK" and c["alerta_ai"] != c["alerta_regula"]
        else ("" if c["status"] == "OK" else BADGE_FAIL_BLOC),
        "if({cond}, concat({a}, {r}, {b}), if(equals({s}, 'OK'), '', {f}))".format(
            cond=REVIEW_COND, a=pa_str(BADGE_REVIEW_BLOC.split("{r}")[0]), r=_i("alerta_regula"),
            b=pa_str(BADGE_REVIEW_BLOC.split("{r}")[1]), s=_i("status"), f=pa_str(BADGE_FAIL_BLOC))),
    "comentariu": (lambda c: c["comentariu"], _i("comentariu")),
    "actiune": (
        lambda c: ACTIUNE_HTML.format(a=c["actiune"]) if c["actiune"] else "",
        "if(empty({x}), '', concat({a}, {x}, {b}))".format(
            x=_i("actiune"), a=pa_str(ACTIUNE_HTML.split("{a}")[0]), b=pa_str(ACTIUNE_HTML.split("{a}")[1]))),
}

# Items of Filter_Mav = Realizat_Lunar rows of the month with Maverick_RON > 0
MAV_TOKENS = {
    "cheie": (lambda m: m["Title"], _i("Title")),
    "realizat": (lambda m: fmt(m["Suma_RON"], 0), pa_num(_i("Suma_RON"), 0)),
    "aprobat": (lambda m: fmt(m["Aprobat_RON"], 0), pa_num(_i("Aprobat_RON"), 0)),
    "maverick": (lambda m: fmt(m["Maverick_RON"], 0), pa_num(_i("Maverick_RON"), 0)),
}

# Items of varErori: rand, cheie, tip, mesaj
ERR_TOKENS = {
    "rand": (lambda e: str(e["rand"]), _i("rand")),
    "tip": (lambda e: e["tip"], _i("tip")),
    "mesaj": (lambda e: e["mesaj"], _i("mesaj")),
}

FRAGMENTS = {  # file -> (tokens, flow action name, From expression)
    "rand_cc.html": (CC_TOKENS, "Select_Rand_CC", "variables('varRezCC')"),
    "bloc_ai.html": (CC_TOKENS, "Select_Bloc_AI", "variables('varRezCC')"),
    "rand_maverick.html": (MAV_TOKENS, "Select_Rand_Mav", "body('Filter_Mav')"),
    "rand_eroare.html": (ERR_TOKENS, "Select_Rand_Err", "variables('varErori')"),
}

# Page-level placeholders: Power Automate expressions used by Html_Raport.
TOT = "outputs('Tot_Raport')"
PAGE_PA = {
    "LUNA": "outputs('Luna_Import')",
    "FISIER": "variables('varFisier')",
    "RULARE_ID": "variables('varRulare')",
    "CURS_INFO": "concat('BNR ', variables('varDataCurs'), ': EUR ', string(variables('varCursuri')?['EUR']), ', USD ', string(variables('varCursuri')?['USD']))",
    "TOT_BUGET": pa_num(f"{TOT}?['buget']", 0),
    "TOT_REALIZAT": pa_num(f"{TOT}?['realizat']", 0),
    "TOT_VAR_PCT": f"concat({pa_signed(f'{TOT}?[' + chr(39) + 'varianta_pct' + chr(39) + ']', 2)}, '%')",
    "TOT_VAR_CULOARE": f"if(greater(float({TOT}?['varianta_pct']), 0), '{RED}', '{GREEN}')",
    "TOT_MAVERICK": pa_num(f"{TOT}?['maverick']", 0),
    "TOT_MAV_CULOARE": f"if(greater(float({TOT}?['maverick']), 0), '{RED}', '#1f2937')",
    "N_TOTAL": "string(outputs('Sumar_Import')?['total'])",
    "N_VALIDE": "string(outputs('Sumar_Import')?['valide'])",
    "N_INVALIDE": "string(outputs('Sumar_Import')?['invalide'])",
    "N_DUPLICATE": "string(outputs('Sumar_Import')?['duplicate'])",
    "N_AI_OK": "string(outputs('Sumar_Import')?['ai_ok'])",
    "N_AI_ESEC": "string(outputs('Sumar_Import')?['ai_esec'])",
    "PRAG_ALERTA": "string(outputs('cfg')?['prag_alerta_pct'])",
    "ROWS_CC": "join(body('Select_Rand_CC'), '')",
    "BLOCURI_AI": "join(body('Select_Bloc_AI'), '')",
    "ROWS_MAVERICK": f"if(empty(body('Select_Rand_Mav')), {pa_str(EMPTY_MAV)}, join(body('Select_Rand_Mav'), ''))",
    "ROWS_ERORI": f"if(empty(body('Select_Rand_Err')), {pa_str(EMPTY_ERR)}, join(body('Select_Rand_Err'), ''))",
    "DATA_RAPORT": "convertTimeZone(utcNow(), 'UTC', 'GTB Standard Time', 'dd.MM.yyyy HH:mm')",
}

JSON_REZCC_EXPR = "json(concat('{\"r\":{\"c\":', string(variables('varRezCC')), '}}'))"
_X = "xpath(xml(outputs('Json_RezCC')), 'sum(/r/c/{f})')"
TOT_RAPORT_TEXT = """{
  "buget": "@{%s}",
  "realizat": "@{%s}",
  "maverick": "@{%s}",
  "varianta_pct": "@{div(mul(sub(float(%s), float(%s)), 100), max(float(%s), 0.01))}"
}""" % (_X.format(f="buget"), _X.format(f="realizat"), _X.format(f="maverick"),
        _X.format(f="realizat"), _X.format(f="buget"), _X.format(f="buget"))

# ---------------------------------------------------------------- rendering


def fill(text: str, values: dict) -> str:
    missing = set(TOKEN.findall(text)) - set(values)
    if missing:
        raise KeyError(f"no value for {sorted(missing)}")
    return TOKEN.sub(lambda m: values[m.group(1)], text)


def render_fragment(name: str, items: list) -> str:
    tpl = (FRAG / name).read_text(encoding="utf-8").strip()
    tokens = FRAGMENTS[name][0]
    return "".join(fill(tpl, {k: py(it) for k, (py, _) in tokens.items()}) for it in items)


def preview_data() -> dict:
    exp = json.loads((ROOT / "data/expected/expected_results.json").read_text(encoding="utf-8"))
    rez = []
    for c in exp["centre_cost"]:
        ai = json.loads((ROOT / f"ai/samples/r1_{c['cc']}.json").read_text(encoding="utf-8"))["content"]
        rez.append({
            "cc": c["cc"], "buget": c["buget_ron"], "realizat": c["realizat_ron"],
            "varianta_ron": c["varianta_ron"], "varianta_pct": c["varianta_pct"], "maverick": c["maverick_ron"],
            "alerta_regula": c["alerta_regula"], "alerta_ai": ai["nivel_alerta"], "status": "OK",
            "comentariu": ai["comentariu"], "actiune": ai["actiune"],
        })
    mav = [{"Title": r["cheie"], "Suma_RON": r["suma_ron"], "Aprobat_RON": r["aprobat_ron"],
            "Maverick_RON": r["maverick_ron"]} for r in exp["realizat"] if r["maverick_ron"] > 0]
    return {"exp": exp, "rez": rez, "mav": mav, "err": exp["erori"]}


def render_preview() -> Path:
    d = preview_data()
    exp, rez = d["exp"], d["rez"]
    buget = sum(c["buget"] for c in rez)
    realizat = sum(c["realizat"] for c in rez)
    maverick = sum(c["maverick"] for c in rez)
    var_pct = (realizat - buget) * 100 / max(buget, 0.01)
    s = exp["sumar"]
    cur = exp["cursuri"]
    page = {
        "LUNA": exp["luna"], "FISIER": exp["fisier"], "RULARE_ID": "preview",
        "CURS_INFO": f"BNR {cur['data']}: EUR {cur['EUR']}, USD {cur['USD']}",
        "TOT_BUGET": fmt(buget, 0), "TOT_REALIZAT": fmt(realizat, 0),
        "TOT_VAR_PCT": signed(var_pct, 2) + "%", "TOT_VAR_CULOARE": RED if var_pct > 0 else GREEN,
        "TOT_MAVERICK": fmt(maverick, 0), "TOT_MAV_CULOARE": RED if maverick > 0 else "#1f2937",
        "N_TOTAL": str(s["total"]), "N_VALIDE": str(s["valide"]), "N_INVALIDE": str(s["invalide"]),
        "N_DUPLICATE": str(s["duplicate"]), "N_AI_OK": str(len(rez)), "N_AI_ESEC": "0", "PRAG_ALERTA": "10",
        "ROWS_CC": render_fragment("rand_cc.html", rez),
        "BLOCURI_AI": render_fragment("bloc_ai.html", rez),
        "ROWS_MAVERICK": render_fragment("rand_maverick.html", d["mav"]) or EMPTY_MAV,
        "ROWS_ERORI": render_fragment("rand_eroare.html", d["err"]) or EMPTY_ERR,
        "DATA_RAPORT": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    body = fill((REPORT / "template.html").read_text(encoding="utf-8"), page)
    out = REPORT / "preview.html"
    out.write_text('<!doctype html><html lang="ro"><head><meta charset="utf-8"><title>BudgetGuard preview</title></head>'
                   f'<body style="margin:0">{body}</body></html>', encoding="utf-8")
    return out


# ---------------------------------------------------------------- flow expressions


def fragment_expr(name: str) -> str:
    tpl = (FRAG / name).read_text(encoding="utf-8").strip()
    tokens = FRAGMENTS[name][0]
    parts, pos = [], 0
    for m in TOKEN.finditer(tpl):
        if m.start() > pos:
            parts.append(pa_str(tpl[pos:m.start()]))
        parts.append(tokens[m.group(1)][1])
        pos = m.end()
    if pos < len(tpl):
        parts.append(pa_str(tpl[pos:]))
    return "concat(" + ", ".join(parts) + ")"


def html_raport_expr() -> str:
    tpl = (REPORT / "template.html").read_text(encoding="utf-8")
    used = list(dict.fromkeys(TOKEN.findall(tpl)))
    missing = set(used) - set(PAGE_PA)
    if missing:
        raise KeyError(f"no flow expression for {sorted(missing)}")
    expr = "outputs('Sablon_Raport')"
    for k in used:
        expr = f"replace({expr}, '{{{{{k}}}}}', {PAGE_PA[k]})"
    return expr


def write_flow_doc() -> Path:
    if "@" in (REPORT / "template.html").read_text(encoding="utf-8"):
        raise ValueError("template.html contains '@', which the flow designer treats as an expression")
    blocks = []
    for name, (_, action, src) in FRAGMENTS.items():
        e = fragment_expr(name)
        assert len(e) < PA_EXPR_LIMIT, f"{action}: {len(e)} chars"
        blocks.append((action, src, e))
    html = html_raport_expr()
    assert len(html) < PA_EXPR_LIMIT, f"Html_Raport: {len(html)} chars"

    lines = [
        "# Raportul HTML în flux — expresii generate",
        "",
        "> Fișier **generat** de `python report/render_preview.py --flow` din `report/template.html` și "
        "`report/fragments/*.html`. Nu-l edita de mână: modifici șablonul sau fragmentele și regenerezi.",
        "> Pașii de construcție sunt în `docs/flux2_pas_cu_pas.md` (Pasul 9, varianta finală).",
        "",
        "## `Json_RezCC` (Compose, fx)",
        "",
        "```",
        JSON_REZCC_EXPR,
        "```",
        "",
        "## `Tot_Raport` (Compose, lipire directă, fără fx)",
        "",
        "```",
        TOT_RAPORT_TEXT,
        "```",
        "",
    ]
    for action, src, e in blocks:
        lines += [f"## `{action}` (Select, text mode)", "", f"**From**: fx `{src}`", "", "**Map** (fx):", "", "```", e, "```", ""]
    lines += ["## `Html_Raport` (Compose, fx)", "", "```", html, "```", ""]
    out = ROOT / "docs/raport_expresii.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--flow", action="store_true", help="write docs/raport_expresii.md instead of the preview")
    a = ap.parse_args()
    print(write_flow_doc() if a.flow else render_preview())
