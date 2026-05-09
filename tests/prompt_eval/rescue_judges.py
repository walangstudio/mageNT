"""Re-extract scores from judge responses whose nested quotes broke strict JSON parse.

Looks for the 5 `"score": N` integers in document order matched to the 5 dimensions.
Pulls `"total": N` if present; otherwise sums.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
import sys

DIMS = ["opinionatedness", "scope_discipline", "output_structure", "conciseness", "actionability"]


def rescue(raw: str) -> dict | None:
    if not raw:
        return None
    scores = [int(m.group(1)) for m in re.finditer(r'"score"\s*:\s*([1-5])\b', raw)]
    if len(scores) < 5:
        return None
    out = {"scores": {DIMS[i]: {"score": scores[i], "evidence": "(rescued)", "gap": ""}
                       for i in range(5)}}
    m = re.search(r'"total"\s*:\s*(\d+)', raw)
    out["total"] = int(m.group(1)) if m else sum(scores[:5])
    return out


def patch_file(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    runs = data["runs"] if isinstance(data, dict) else data
    fixed = 0
    for r in runs:
        j = r.get("judgment", {})
        if not isinstance(j, dict) or "scores" in j:
            continue
        raw = j.get("raw", "")
        rescued = rescue(raw)
        if rescued:
            r["judgment"] = rescued | {"verdict": "(rescued from non-JSON)"}
            fixed += 1
    if fixed:
        path.write_text(json.dumps(data if isinstance(data, dict) else runs, indent=2),
                        encoding="utf-8")
    return fixed


if __name__ == "__main__":
    for p in sys.argv[1:]:
        n = patch_file(Path(p))
        print(f"{p}: rescued {n}")
