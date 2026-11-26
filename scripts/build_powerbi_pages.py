"""Write the two BudgetGuard report pages, and the report theme, into the Power BI project (PBIR).

Power BI Desktop must be CLOSED while this runs, otherwise it overwrites the files on save.
Idempotent: page 1 keeps its folder and the month slicer the user configured; every other
visual on page 1 and the whole of page 2 are regenerated on each run.

Also patches the semantic model (TMDL) once:
  - relationship Analize[CentruCost] -> CC[CC]
  - measure _Masuri[Maverick culoare] (background for the maverick matrix)

Usage: python scripts/build_powerbi_pages.py
"""
import json
import pathlib
import shutil
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORT = ROOT / "powerbi" / "BudgetGuard.Report" / "definition"
MODEL = ROOT / "powerbi" / "BudgetGuard.SemanticModel" / "definition"
PAGES = REPORT / "pages"
VC_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/1.3.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.2.0/schema.json"
PAGE2 = "c0ffee00b6d9e1a2f3a4"
THEME_FILE = "BudgetGuard_theme.json"

# Same palette as the HTML e-mail report
NAVY, BLUE, AMBER, GREEN, RED = "#1e3a8a", "#60a5fa", "#f59e0b", "#15803d", "#b42318"
TOP = 66      # content starts below the 56 px header band
GAP = 10


# ---------------------------------------------------------------- semantic model patches

def patch_model() -> None:
    rel = MODEL / "relationships.tmdl"
    text = rel.read_text(encoding="utf-8")
    if "fromColumn: Analize.CentruCost" not in text:
        text = text.rstrip("\n") + (
            f"\n\nrelationship {uuid.uuid4()}\n"
            "\tfromColumn: Analize.CentruCost\n"
            "\ttoColumn: CC.CC\n"
        )
        rel.write_text(text, encoding="utf-8")
        print("model: added relationship Analize.CentruCost -> CC.CC")

    tbl = MODEL / "tables" / "_Masuri.tmdl"
    text = tbl.read_text(encoding="utf-8")
    if "measure 'Maverick culoare'" not in text:
        head, sep, rest = text.partition("\n\n")  # after "table _Masuri" + its lineageTag
        measure = (
            "\tmeasure 'Maverick culoare' = IF ( [Maverick] > 0, \"#fee4e2\" )\n"
            f"\t\tlineageTag: {uuid.uuid4()}\n"
        )
        tbl.write_text(head + sep + measure + "\n" + rest, encoding="utf-8")
        print("model: added measure Maverick culoare")


# ---------------------------------------------------------------- theme

def solid(h: str) -> dict:
    return {"solid": {"color": h}}


THEME = {
    "name": "BudgetGuard",
    "dataColors": [NAVY, BLUE, AMBER, GREEN, RED, "#b45309", "#64748b", "#a78bfa", "#0e7490", "#be185d"],
    "foreground": "#1f2937",
    "foregroundNeutralSecondary": "#4b5563",
    "foregroundNeutralTertiary": "#9ca3af",
    "background": "#ffffff",
    "backgroundLight": "#f9fafb",
    "backgroundNeutral": "#e5e7eb",
    "tableAccent": NAVY,
    "good": GREEN, "neutral": "#b45309", "bad": RED,
    "maximum": NAVY, "center": BLUE, "minimum": "#dbeafe",
    "textClasses": {
        "callout": {"fontSize": 24, "fontFace": "Segoe UI Semibold", "color": "#111827"},
        "title": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#111827"},
        "header": {"fontSize": 10, "fontFace": "Segoe UI Semibold", "color": "#4b5563"},
        "label": {"fontSize": 10, "fontFace": "Segoe UI", "color": "#374151"},
    },
    "visualStyles": {
        "page": {"*": {
            "background": [{"color": solid("#f3f4f6"), "transparency": 0}],
            "outspace": [{"color": solid("#f3f4f6"), "transparency": 0}],
        }},
        "*": {"*": {
            "background": [{"show": True, "color": solid("#ffffff"), "transparency": 0}],
            "border": [{"show": True, "color": solid("#e5e7eb"), "radius": 6}],
            "dropShadow": [{"show": False}],
            "padding": [{"top": 8, "bottom": 8, "left": 12, "right": 12}],
            "title": [{"fontColor": solid("#111827"), "fontSize": 12, "fontFamily": "Segoe UI Semibold"}],
        }},
        "card": {"*": {
            "labels": [{"fontSize": 24, "fontFamily": "Segoe UI Semibold", "color": solid("#111827")}],
            "categoryLabels": [{"show": True, "fontSize": 10, "color": solid("#6b7280")}],
        }},
        "tableEx": {"*": {
            "columnHeaders": [{"fontColor": solid("#4b5563"), "backColor": solid("#f9fafb"),
                               "fontFamily": "Segoe UI Semibold", "fontSize": 10}],
            "values": [{"fontSize": 10, "backColorPrimary": solid("#ffffff"), "backColorSecondary": solid("#f9fafb")}],
            "grid": [{"gridVertical": False, "gridHorizontal": True, "gridHorizontalColor": solid("#e5e7eb"),
                      "outlineColor": solid("#e5e7eb")}],
            "total": [{"fontFamily": "Segoe UI Semibold", "backColor": solid("#eef2ff")}],
        }},
        "pivotTable": {"*": {
            "columnHeaders": [{"fontColor": solid("#4b5563"), "backColor": solid("#f9fafb"),
                               "fontFamily": "Segoe UI Semibold", "fontSize": 10}],
            "rowHeaders": [{"fontFamily": "Segoe UI Semibold", "fontSize": 10}],
            "values": [{"fontSize": 10}],
            "grid": [{"gridVertical": False, "gridHorizontal": True, "gridHorizontalColor": solid("#e5e7eb"),
                      "outlineColor": solid("#e5e7eb")}],
            "total": [{"fontFamily": "Segoe UI Semibold", "backColor": solid("#eef2ff")}],
        }},
    },
}


def install_theme() -> None:
    res = REPORT.parent / "StaticResources" / "RegisteredResources"
    res.mkdir(parents=True, exist_ok=True)
    (res / THEME_FILE).write_text(json.dumps(THEME, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    path = REPORT / "report.json"
    rep = json.loads(path.read_text(encoding="utf-8"))
    rep["themeCollection"]["customTheme"] = {
        "name": THEME_FILE,
        "reportVersionAtImport": rep["themeCollection"]["baseTheme"]["reportVersionAtImport"],
        "type": "RegisteredResources",
    }
    pkgs = [p for p in rep["resourcePackages"] if p["name"] != "RegisteredResources"]
    pkgs.append({"name": "RegisteredResources", "type": "RegisteredResources",
                 "items": [{"name": THEME_FILE, "path": THEME_FILE, "type": "CustomTheme"}]})
    rep["resourcePackages"] = pkgs
    path.write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- PBIR helpers

def lit(v: str) -> dict:
    return {"expr": {"Literal": {"Value": v}}}


def text_lit(s: str) -> dict:
    return lit("'" + s.replace("'", "''") + "'")


def color_hex(h: str) -> dict:
    return {"solid": {"color": lit(f"'{h}'")}}


def measure_expr(name: str) -> dict:
    return {"Measure": {"Expression": {"SourceRef": {"Entity": "_Masuri"}}, "Property": name}}


def column_expr(table: str, col: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": col}}


def color_from_measure(name: str) -> dict:
    return {"solid": {"color": {"expr": measure_expr(name)}}}


def m(name: str, label: str = None) -> dict:
    p = {"field": measure_expr(name), "queryRef": f"_Masuri.{name}", "nativeQueryRef": name}
    if label:
        p["displayName"] = label
    return p


def c(table: str, col: str, label: str = None) -> dict:
    p = {"field": column_expr(table, col), "queryRef": f"{table}.{col}", "nativeQueryRef": col}
    if label:
        p["displayName"] = label
    return p


def column_format(metadata: str, **props) -> dict:
    """Per-column formatting in a table/matrix (conditional colours)."""
    return {"properties": props,
            "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": metadata}}


def widths(**cols) -> list:
    """Fixed column widths for a table: queryRef -> pixels."""
    return [{"properties": {"value": lit(f"{w}D")}, "selector": {"metadata": ref}} for ref, w in cols.items()]


def series_colors(**refs) -> list:
    return [{"properties": {"fill": color_hex(col)}, "selector": {"metadata": ref}} for ref, col in refs.items()]


def visual(name, vtype, x, y, w, h, z, roles, title=None, objects=None) -> dict:
    v = {
        "$schema": VC_SCHEMA,
        "name": name,
        "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z},
        "visual": {
            "visualType": vtype,
            "query": {"queryState": {role: {"projections": projs} for role, projs in roles.items()}},
            "drillFilterOtherVisuals": True,
        },
    }
    if objects:
        v["visual"]["objects"] = objects
    if title:
        v["visual"]["visualContainerObjects"] = {
            "title": [{"properties": {"show": lit("true"), "text": text_lit(title)}}]
        }
    return v


def card(name, measure, x, y, w, h, z, label, color_measure=None) -> dict:
    labels = {"fontSize": lit("24D"), "labelDisplayUnits": lit("1D")}
    if color_measure:
        labels["color"] = color_from_measure(color_measure)
    objects = {
        "labels": [{"properties": labels}],
        "categoryLabels": [{"properties": {"show": lit("true"), "fontSize": lit("10D")}}],
    }
    return visual(name, "card", x, y, w, h, z, {"Values": [m(measure, label)]}, objects=objects)


def header(name: str, title: str, subtitle: str) -> dict:
    def run(value, size, color, bold=False):
        style = {"fontSize": size, "color": color, "fontFamily": "Segoe UI Semibold" if bold else "Segoe UI"}
        if bold:
            style["fontWeight"] = "bold"
        return {"value": value, "textStyle": style}

    return {
        "$schema": VC_SCHEMA,
        "name": name,
        "position": {"x": 0, "y": 0, "z": 0, "height": 56, "width": 1280, "tabOrder": 0},
        "visual": {
            "visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": [
                {"textRuns": [run("BudgetGuard", "16pt", "#ffffff", True),
                              run("   ·   " + title, "16pt", "#ffffff")]},
                {"textRuns": [run(subtitle, "9pt", "#c7d2fe")]},
            ]}}]},
            "visualContainerObjects": {
                "background": [{"properties": {"show": lit("true"), "color": color_hex(NAVY),
                                               "transparency": lit("0D")}}],
                "border": [{"properties": {"show": lit("false")}}],
            },
            "drillFilterOtherVisuals": True,
        },
    }


def write_visual(page_dir: pathlib.Path, v: dict) -> None:
    d = page_dir / "visuals" / v["name"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "visual.json").write_text(json.dumps(v, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- page 1: Budget vs. actual

def build_page1(page_dir: pathlib.Path) -> None:
    keep = None
    for vdir in (page_dir / "visuals").iterdir():
        vj = json.loads((vdir / "visual.json").read_text(encoding="utf-8"))
        if vj.get("visual", {}).get("visualType") == "slicer":
            keep = vdir.name
            vj["position"].update({"x": 10, "y": TOP, "width": 200, "height": 84, "z": 500, "tabOrder": 500})
            (vdir / "visual.json").write_text(json.dumps(vj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        else:
            shutil.rmtree(vdir)
    if keep is None:
        print("warning: no month slicer found on page 1; add one in Power BI (Luni[Luna afisata])")

    row2, row3 = TOP + 84 + GAP, TOP + 84 + GAP + 270 + GAP
    visuals = [
        header("p1header", "Buget vs. Realizat",
               "Vestra Retail SRL  ·  bugete, cheltuieli realizate și analiza AI pe centre de cost  ·  "
               "sursa: listele SharePoint BudgetGuard"),
        card("p1card_buget", "Buget", 220, TOP, 255, 84, 1000, "Buget (RON)"),
        card("p1card_realizat", "Realizat", 485, TOP, 255, 84, 2000, "Realizat (RON)"),
        card("p1card_varianta", "Varianta %", 750, TOP, 255, 84, 3000, "Varianță față de buget",
             color_measure="Alerta culoare"),
        card("p1card_maverick", "Maverick", 1015, TOP, 255, 84, 4000, "Fără cerere aprobată (RON)"),
        visual(
            "p1chart_cc", "clusteredColumnChart", 10, row2, 620, 270, 5000,
            {"Category": [c("CC", "CC", "Centru de cost")], "Y": [m("Buget"), m("Angajat"), m("Realizat")]},
            title="Buget, angajat și realizat pe centru de cost",
            objects={"dataPoint": series_colors(**{
                "_Masuri.Buget": NAVY, "_Masuri.Angajat": BLUE, "_Masuri.Realizat": AMBER})},
        ),
        visual(
            "p1table_cc", "tableEx", 640, row2, 630, 270, 6000,
            {"Values": [c("CC", "CC", "Centru de cost"), m("Buget"), m("Realizat"), m("Varianta %", "Varianță"),
                        m("Maverick", "Fără cerere"), m("Alerta", "Alertă")]},
            title="Alertă pe centru de cost",
            objects={"values": [column_format(
                "_Masuri.Alerta", backColor=color_from_measure("Alerta culoare"), fontColor=color_hex("#FFFFFF"))]},
        ),
        visual(
            "p1matrix_mav", "pivotTable", 10, row3, 420, 720 - row3 - GAP, 7000,
            {"Rows": [c("CC", "CC", "CC")], "Columns": [c("CAT", "CAT", "Categorie")],
             "Values": [m("Maverick", "Fără cerere")]},
            title="Cheltuieli fără cerere aprobată (maverick)",
            objects={"values": [column_format("_Masuri.Maverick", backColor=color_from_measure("Maverick culoare"))]},
        ),
        visual(
            "p1table_ai", "tableEx", 440, row3, 830, 720 - row3 - GAP, 8000,
            {"Values": [
                c("Analize", "CentruCost", "CC"), c("Analize", "Alerta_Regula", "Regulă"),
                c("Analize", "Alerta_AI", "AI"), c("Analize", "Necesita_Revizuire", "Revizuire"),
                c("Analize", "Comentariu_AI", "Comentariul analistului AI"),
            ]},
            title="Analiza AI pe centre de cost",
            objects={
                "values": [{"properties": {"wordWrap": lit("true")}}],
                "columnWidth": widths(**{
                    "Analize.CentruCost": 50, "Analize.Alerta_Regula": 70, "Analize.Alerta_AI": 70,
                    "Analize.Necesita_Revizuire": 80, "Analize.Comentariu_AI": 520,
                }),
            },
        ),
    ]
    for v in visuals:
        write_visual(page_dir, v)


# ---------------------------------------------------------------- page 2: approval pipeline

def build_page2() -> None:
    page_dir = PAGES / PAGE2
    if page_dir.exists():
        shutil.rmtree(page_dir)
    page_dir.mkdir(parents=True)
    (page_dir / "page.json").write_text(json.dumps({
        "$schema": PAGE_SCHEMA,
        "name": PAGE2,
        "displayName": "Pipeline aprobări",
        "displayOption": "FitToPage",
        "height": 720,
        "width": 1280,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    row2, row3 = TOP + 84 + GAP, TOP + 84 + GAP + 260 + GAP
    visuals = [
        header("p2header", "Pipeline aprobări",
               "Cereri de achiziție: status, volum, timp de aprobare și respingeri  ·  "
               "sursa: lista SharePoint Cereri_Achizitie"),
        card("p2card_nr", "Nr cereri", 10, TOP, 307, 84, 1000, "Cereri"),
        card("p2card_valoare", "Valoare aprobata", 327, TOP, 307, 84, 2000, "Valoare aprobată (RON)"),
        card("p2card_timp", "Timp mediu aprobare (ore)", 644, TOP, 307, 84, 3000, "Timp mediu de aprobare (ore)"),
        card("p2card_respingere", "Rata respingere", 961, TOP, 309, 84, 4000, "Rată de respingere"),
        visual(
            "p2donut_status", "donutChart", 10, row2, 400, 260, 5000,
            {"Category": [c("Cereri", "Status")], "Y": [m("Nr cereri", "Cereri")]},
            title="Cereri pe status",
        ),
        visual(
            "p2line_zi", "lineChart", 420, row2, 430, 260, 6000,
            {"Category": [c("Calendar", "Date", "Data")], "Y": [m("Nr cereri", "Cereri")]},
            title="Cereri depuse pe zi",
            objects={"dataPoint": series_colors(**{"_Masuri.Nr cereri": NAVY})},
        ),
        visual(
            "p2bar_cc", "clusteredBarChart", 860, row2, 410, 260, 7000,
            {"Category": [c("CC", "CC", "Centru de cost")],
             "Y": [m("Cereri aprobate", "Aprobate"), m("Cereri respinse", "Respinse")]},
            title="Aprobate și respinse pe centru de cost",
            objects={"dataPoint": series_colors(**{"_Masuri.Cereri aprobate": GREEN, "_Masuri.Cereri respinse": RED})},
        ),
        visual(
            "p2table_cereri", "tableEx", 10, row3, 1260, 720 - row3 - GAP, 8000,
            {"Values": [
                c("Cereri", "Title", "ID cerere"), c("Cereri", "TitluCerere", "Titlu"),
                c("Cereri", "CentruCost", "CC"), c("Cereri", "Valoare_RON", "Valoare (RON)"),
                c("Cereri", "Status"), c("Cereri", "Peste_Buget", "Peste buget"),
                c("Cereri", "Data_Cerere", "Data cererii"),
            ]},
            title="Cereri de achiziție",
        ),
    ]
    for v in visuals:
        write_visual(page_dir, v)


def main() -> None:
    patch_model()
    install_theme()
    pages_meta = json.loads((PAGES / "pages.json").read_text(encoding="utf-8"))
    page1 = next(p for p in pages_meta["pageOrder"] if p != PAGE2)
    build_page1(PAGES / page1)
    build_page2()
    pages_meta["pageOrder"] = [page1, PAGE2]
    pages_meta["activePageName"] = page1
    (PAGES / "pages.json").write_text(json.dumps(pages_meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for p in (page1, PAGE2):
        print(f"page {p}: {len(list((PAGES / p / 'visuals').iterdir()))} visuals")


if __name__ == "__main__":
    main()
