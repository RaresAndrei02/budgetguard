"""Unpack an exported Power Automate solution ZIP into solution/src, with secrets removed.

Power Automate copies the *current value* of environment variables into each flow
definition (parameters.<name>.defaultValue), so a solution exported while the
Groq key is set carries the key in clear text. This script blanks those values,
pretty-prints the JSON (stable, reviewable diffs), drops the GUID suffix from
workflow file names, and refuses to finish if anything key-like is left.

Usage: python scripts/unpack_solution.py path/to/BudgetGuard_x_y_z_w.zip
"""
import json
import pathlib
import re
import shutil
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "solution" / "src"
SECRET_PARAM = re.compile(r"api ?key|secret|token|password", re.IGNORECASE)
SECRET_VALUE = re.compile(r"gsk_[A-Za-z0-9]{10,}|AIza[0-9A-Za-z_\-]{20,}|sk-[A-Za-z0-9]{20,}")


def scrub(defn: dict, name: str) -> int:
    """Blank defaultValue of secret-looking parameters; return how many were blanked."""
    n = 0
    params = defn.get("properties", {}).get("definition", {}).get("parameters", {})
    for pname, p in params.items():
        if isinstance(p, dict) and "defaultValue" in p and SECRET_PARAM.search(pname):
            if p["defaultValue"]:
                p["defaultValue"] = ""
                n += 1
                print(f"  blanked {name}: parameter '{pname}'")
    return n


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    zpath = pathlib.Path(sys.argv[1])
    if OUT.exists():
        shutil.rmtree(OUT)
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if name.startswith("Workflows/"):
                name = "Workflows/" + name.split("/", 1)[1].rsplit("-", 5)[0] + ".json"
            dst = OUT / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            raw = z.read(info)
            if dst.suffix == ".json":
                data = json.loads(raw.decode("utf-8-sig"))
                scrub(data, name)
                raw = (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
            dst.write_bytes(raw)

    leaks = [f"{p.relative_to(ROOT)}:{i}" for p in OUT.rglob("*") if p.is_file()
             for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1)
             if SECRET_VALUE.search(line)]
    if leaks:
        shutil.rmtree(OUT)
        print("Secret-like values still present; nothing written:\n" + "\n".join(leaks))
        return 1
    print(f"Unpacked {zpath.name} into {OUT.relative_to(ROOT)} (no secrets found).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
