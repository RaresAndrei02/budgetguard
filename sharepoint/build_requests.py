"""schema.json + data/seed/*.csv -> SharePoint REST request arrays for the BG_Setup_SharePoint flow.

Outputs:
  sharepoint/provision_requests.json  lists, Title rename/index, columns, libraries, folders
  sharepoint/seed_requests.json       seed items (Config, Nomenclator, Bugete, Cereri_Achizitie)
  docs/sharepoint_schema.md           human-readable schema (Romanian)

Each request: {"method", "uri", "headers", "body"}; "uri" is relative to the site
(used as-is in "Send an HTTP request to SharePoint").
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent

VERBOSE = {"Accept": "application/json;odata=verbose", "Content-Type": "application/json;odata=verbose"}
MERGE = {**VERBOSE, "X-HTTP-Method": "MERGE", "IF-MATCH": "*"}
NOMETA = {"Accept": "application/json;odata=nometadata", "Content-Type": "application/json;odata=nometadata"}

SEED_FILES = [
    ("Config", "config.csv"),
    ("Nomenclator", "nomenclator.csv"),
    ("Bugete", "bugete.csv"),
    ("Cereri_Achizitie", "cereri_istorice_2026-10.csv"),
]
TYPE_RO = {
    "Text": "Text (o linie)", "Note": "Text pe mai multe linii", "Number": "Număr", "Boolean": "Da/Nu",
    "DateTime": "Dată și oră", "Choice": "Alegere",
}


def field_xml(f: dict) -> str:
    n = f["name"]
    base = f"DisplayName='{n}' Name='{n}' StaticName='{n}'"
    t = f["type"]
    if t == "Text":
        return f"<Field Type='Text' {base} MaxLength='255' />"
    if t == "Note":
        return f"<Field Type='Note' {base} NumLines='6' RichText='FALSE' />"
    if t == "Number":
        return f"<Field Type='Number' {base} Decimals='{f.get('decimals', 2)}' />"
    if t == "Boolean":
        return f"<Field Type='Boolean' {base}><Default>0</Default></Field>"
    if t == "DateTime":
        fmt = "DateOnly" if f.get("date_only") else "DateTime"
        return f"<Field Type='DateTime' {base} Format='{fmt}' />"
    if t == "Choice":
        ch = "".join(f"<CHOICE>{escape(c)}</CHOICE>" for c in f["choices"])
        default = f"<Default>{escape(f['default'])}</Default>" if f.get("default") else ""
        return f"<Field Type='Choice' {base} Format='Dropdown'><CHOICES>{ch}</CHOICES>{default}</Field>"
    raise ValueError(t)


def lst(title: str) -> str:
    return f"_api/web/lists/getbytitle('{title}')"


def provision(schema: dict) -> list[dict]:
    reqs = []
    for L in schema["lists"]:
        reqs.append({"method": "POST", "uri": "_api/web/lists", "headers": VERBOSE, "body": {
            "__metadata": {"type": "SP.List"}, "BaseTemplate": 100, "Title": L["title"],
            "Description": L.get("description", ""), "AllowContentTypes": True, "ContentTypesEnabled": False}})
        title_body = {"__metadata": {"type": "SP.Field"}, "Title": L["title_display"]}
        if L.get("unique_title"):
            title_body.update({"Indexed": True, "EnforceUniqueValues": True})
        reqs.append({"method": "POST", "uri": f"{lst(L['title'])}/fields/getbyinternalnameortitle('Title')",
                     "headers": MERGE, "body": title_body})
        for f in L["fields"]:
            reqs.append({"method": "POST", "uri": f"{lst(L['title'])}/fields/createfieldasxml", "headers": VERBOSE,
                         "body": {"parameters": {"__metadata": {"type": "SP.XmlSchemaFieldCreationInformation"},
                                                 "SchemaXml": field_xml(f), "Options": 24}}})
    for lib in schema["libraries"]:
        reqs.append({"method": "POST", "uri": "_api/web/lists", "headers": VERBOSE, "body": {
            "__metadata": {"type": "SP.List"}, "BaseTemplate": 101, "Title": lib["title"],
            "Description": lib.get("description", "")}})
        for folder in lib.get("folders", []):
            reqs.append({"method": "POST",
                         "uri": f"_api/web/getfolderbyserverrelativeurl('{lib['title']}')/folders/add('{folder}')",
                         "headers": VERBOSE, "body": None})
    return reqs


def coerce(value: str, ftype: str | None):
    if value is None or value == "":
        return None
    if ftype == "Number":
        return float(value)
    if ftype == "Boolean":
        return value.strip().lower() in ("true", "1", "da", "yes")
    return value


def seed(schema: dict) -> list[dict]:
    types = {L["title"]: {f["name"]: f["type"] for f in L["fields"]} for L in schema["lists"]}
    reqs = []
    for title, fname in SEED_FILES:
        with (ROOT / "data" / "seed" / fname).open(encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                body = {}
                for k, v in row.items():
                    if k != "Title" and k not in types[title]:
                        raise KeyError(f"{fname}: column {k} not in schema for {title}")
                    val = coerce(v, types[title].get(k))
                    if val is not None:
                        body[k] = val
                reqs.append({"method": "POST", "uri": f"{lst(title)}/items", "headers": NOMETA, "body": body})
    return reqs


def schema_md(schema: dict, n_prov: int, n_seed: int) -> str:
    o = ["# Schema SharePoint — BudgetGuard", "",
         "> Generat automat din `sharepoint/schema.json` de `sharepoint/build_requests.py`. Nu edita manual.", "",
         "Site: `<SITE_URL>` (adresa reală e doar în `.env`, cheia `SP_SITE_URL`).",
         "Numele interne ale coloanelor nu au diacritice sau spații. Coloana `Title` e cheia listei și apare sub numele afișat din tabel.", "",
         "## Liste", ""]
    for L in schema["lists"]:
        uniq = " — **valori unice, indexată**" if L.get("unique_title") else ""
        o += [f"### {L['title']}", "", L.get("description", ""), "",
              "| Coloană (nume intern) | Tip | Detalii |", "|---|---|---|",
              f"| `Title` (afișat „{L['title_display']}”) | Text | cheia listei{uniq} |"]
        for f in L["fields"]:
            det = []
            if f["type"] == "Choice":
                det.append("opțiuni: " + ", ".join(f["choices"]))
            if f.get("default"):
                det.append(f"implicit: {f['default']}")
            if f["type"] == "Number":
                det.append(f"{f.get('decimals', 2)} zecimale")
            if f["type"] == "DateTime":
                det.append("doar dată" if f.get("date_only") else "dată + oră (UTC)")
            o.append(f"| `{f['name']}` | {TYPE_RO[f['type']]} | {'; '.join(det)} |")
        o.append("")
    o += ["## Biblioteci de documente", ""]
    for lib in schema["libraries"]:
        folders = ", ".join(f"`{x}`" for x in lib.get("folders", [])) or "—"
        o.append(f"- **{lib['title']}** — {lib.get('description', '')} Subfoldere: {folders}")
    o += ["", "## Fișiere generate", "",
          f"- `sharepoint/provision_requests.json`: {n_prov} cereri REST (liste, coloane, biblioteci, foldere)",
          f"- `sharepoint/seed_requests.json`: {n_seed} cereri REST (datele inițiale din `data/seed/`)", ""]
    return "\n".join(o)


def main():
    schema = json.loads((HERE / "schema.json").read_text(encoding="utf-8"))
    prov, sd = provision(schema), seed(schema)
    # compact JSON: these files are pasted into a Compose action in Power Automate
    compact = {"ensure_ascii": False, "separators": (",", ":")}
    (HERE / "provision_requests.json").write_text(json.dumps(prov, **compact), encoding="utf-8")
    (HERE / "seed_requests.json").write_text(json.dumps(sd, **compact), encoding="utf-8")
    (ROOT / "docs" / "sharepoint_schema.md").write_text(schema_md(schema, len(prov), len(sd)), encoding="utf-8")
    print(f"provision_requests.json: {len(prov)} requests; seed_requests.json: {len(sd)} requests")


if __name__ == "__main__":
    main()
