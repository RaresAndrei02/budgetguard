"""Calibrate the Flux 2 AI prompt locally against the expected results.

For each of the 5 cost centres in data/expected/expected_results.json it builds the
same compact `user` message that Flux 2 will send, calls Groq in JSON mode, validates
the answer against ai/response_schema.json and compares `nivel_alerta` with
`alerta_ai_asteptata` (rule + maverick bump). Repeats the whole set --rounds times.

Acceptance criterion: valid JSON in every call, and nivel_alerta equal to
the expected alert for every cost centre, in all rounds.

Reads GROQ_API_KEY / GROQ_MODEL from .env. Never prints the key.
Usage: python ai/test_prompt.py [--rounds 5] [--model openai/gpt-oss-120b] [--cc HR]
"""
import argparse
import json
import os
import pathlib
import re
import sys
import time

import jsonschema
import requests
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
AI = ROOT / "ai"
URL = "https://api.groq.com/openai/v1/chat/completions"


def load_config() -> dict:
    import csv
    with open(ROOT / "data" / "seed" / "config.csv", encoding="utf-8-sig", newline="") as f:
        return {r["Title"]: r["Valoare"] for r in csv.DictReader(f)}


def user_payload(cc: dict, prag_alerta: float) -> dict:
    """The exact object Flux 2 serialises as the `user` message (keep in sync with docs/flux2_pas_cu_pas.md)."""
    return {
        "luna": cc["luna"],
        "centru_cost": cc["cc"],
        "buget_ron": cc["buget_ron"],
        "angajat_ron": cc["angajat_ron"],
        "realizat_ron": cc["realizat_ron"],
        "varianta_ron": cc["varianta_ron"],
        "varianta_pct": cc["varianta_pct"],
        "maverick_ron": cc["maverick_ron"],
        "praguri": {"verde_max_pct": 5, "galben_max_pct": prag_alerta},
        "categorii": cc["categorii"],
    }


def call_groq(key: str, model: str, system: str, user: dict, retries: int = 4) -> tuple[dict, float]:
    body = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False, separators=(",", ":"))},
        ],
    }
    for attempt in range(retries):
        t0 = time.time()
        r = requests.post(URL, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=90)
        dt = time.time() - t0
        if r.status_code == 429 or r.status_code >= 500:
            wait = float(r.headers.get("retry-after", 2 ** (attempt + 2)))
            print(f"    HTTP {r.status_code}, retry in {wait:.0f}s")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json(), dt
    raise RuntimeError("Groq: too many retries")


def quality_notes(ans: dict, cc: dict) -> list[str]:
    """Soft checks (reported, not part of the acceptance criterion)."""
    notes = []
    if not 1 <= len(ans.get("cauze", [])) <= 3:
        notes.append(f"cauze={len(ans.get('cauze', []))}")
    sentences = [s for s in re.split(r"[.!?](?=\s+[A-ZĂÂÎȘȚ]|\s*$)", ans.get("comentariu", "")) if s.strip()]
    if not 2 <= len(sentences) <= 4:
        notes.append(f"fraze≈{len(sentences)}")
    txt = json.dumps(ans, ensure_ascii=False)
    if "ţ" in txt or "ş" in txt:
        notes.append("diacritice cu sedilă")
    if cc["maverick_ron"] > 0 and "maverick" not in json.dumps(ans, ensure_ascii=False).lower() \
            and "fără cerere" not in json.dumps(ans, ensure_ascii=False).lower():
        notes.append("maverick nemenționat")
    return notes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--model")
    ap.add_argument("--cc", help="run only this cost centre")
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    key = os.getenv("GROQ_API_KEY", "").strip()
    model = (args.model or os.getenv("GROQ_MODEL", "")).strip()
    if not key or not model:
        print("GROQ_API_KEY / GROQ_MODEL missing in .env")
        return 1

    system = (AI / "system_prompt.txt").read_text(encoding="utf-8").strip()
    schema = json.loads((AI / "response_schema.json").read_text(encoding="utf-8"))
    expected = json.loads((ROOT / "data" / "expected" / "expected_results.json").read_text(encoding="utf-8"))
    prag = float(load_config()["prag_alerta_pct"])
    centres = [c for c in expected["centre_cost"] if not args.cc or c["cc"] == args.cc.upper()]

    out = AI / "samples"
    out.mkdir(exist_ok=True)
    for c in centres:  # the user messages, reused as examples in the Flux 2 guide
        (out / f"user_{c['cc']}.json").write_text(
            json.dumps(user_payload(c, prag), ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"model={model} rounds={args.rounds} centres={[c['cc'] for c in centres]}\n")
    results, ok_all = [], True
    for rnd in range(1, args.rounds + 1):
        for c in centres:
            resp, dt = call_groq(key, model, system, user_payload(c, prag))
            content = resp["choices"][0]["message"]["content"]
            row = {"round": rnd, "cc": c["cc"], "expected": c["alerta_ai_asteptata"], "seconds": round(dt, 1),
                   "tokens": resp.get("usage", {}).get("total_tokens")}
            try:
                ans = json.loads(content)
                jsonschema.validate(ans, schema)
                row.update(valid=True, got=ans["nivel_alerta"], notes=quality_notes(ans, c))
            except (json.JSONDecodeError, jsonschema.ValidationError) as e:
                ans = None
                row.update(valid=False, got=None, notes=[f"invalid: {str(e)[:80]}"])
            row["match"] = row["got"] == row["expected"]
            ok_all &= row["valid"] and row["match"]
            results.append(row)
            if rnd == 1 or not (row["valid"] and row["match"]):
                (out / f"r{rnd}_{c['cc']}.json").write_text(
                    json.dumps({"user": user_payload(c, prag), "content": ans or content,
                                "reasoning": resp["choices"][0]["message"].get("reasoning"),
                                "usage": resp.get("usage")}, ensure_ascii=False, indent=2), encoding="utf-8")
            flag = "OK " if row["valid"] and row["match"] else "BAD"
            print(f"  r{rnd} {c['cc']:<4} {flag} expected={row['expected']:<7} got={str(row['got']):<7} "
                  f"{row['seconds']:>5}s tok={row['tokens']} {' '.join(row['notes'])}")
            time.sleep(1.5)  # stay well under the free-tier RPM limit

    n = len(results)
    summary = {
        "model": model, "rounds": args.rounds, "calls": n,
        "valid_json": sum(r["valid"] for r in results), "alert_match": sum(r["match"] for r in results),
        "accepted": ok_all, "results": results,
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nvalid JSON {summary['valid_json']}/{n} · alert match {summary['alert_match']}/{n} · "
          f"{'ACCEPTED' if ok_all else 'NOT accepted'}")
    return 0 if ok_all else 2


if __name__ == "__main__":
    sys.exit(main())
