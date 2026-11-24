"""List the Groq models currently available and make one JSON-mode test call.

Reads GROQ_API_KEY (and optionally GROQ_MODEL) from .env. Never prints the key.
Usage: python scripts/check_groq.py [--list-only] [model_id]
"""
import json
import os
import pathlib
import sys

import requests
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = "https://api.groq.com/openai/v1"


def main() -> int:
    load_dotenv(ROOT / ".env")
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        print("GROQ_API_KEY missing in .env")
        return 1
    headers = {"Authorization": f"Bearer {key}"}

    r = requests.get(f"{BASE}/models", headers=headers, timeout=30)
    print(f"GET /models -> HTTP {r.status_code}")
    r.raise_for_status()
    models = sorted(r.json()["data"], key=lambda m: m["id"])
    (ROOT / "samples" / "groq_models.json").write_text(
        json.dumps(models, indent=2), encoding="utf-8"
    )
    for m in models:
        print(f"  {m['id']:<50} owner={m.get('owned_by')} ctx={m.get('context_window')} active={m.get('active')}")

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--list-only" in sys.argv:
        return 0
    model = (args[0] if args else os.getenv("GROQ_MODEL", "")).strip()
    if not model:
        print("No model given; pass one as argument.")
        return 0

    body = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Răspunde EXCLUSIV cu un obiect JSON valid cu cheile: comentariu (string), nivel_alerta (Verde|Galben|Roșu)."},
            {"role": "user", "content": json.dumps({"centru_cost": "IT", "buget_ron": 100000, "realizat_ron": 118000}, ensure_ascii=False)},
        ],
    }
    r = requests.post(f"{BASE}/chat/completions", headers=headers, json=body, timeout=60)
    print(f"POST /chat/completions ({model}) -> HTTP {r.status_code}")
    r.raise_for_status()
    resp = r.json()
    (ROOT / "samples" / "groq_chat_response.json").write_text(
        json.dumps(resp, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    content = resp["choices"][0]["message"]["content"]
    print("content:", content)
    print("parsed :", json.loads(content))
    print("usage  :", resp.get("usage"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
