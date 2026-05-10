"""Raw baseline: send a single 'build me a todo CLI' prompt to gpt-oss-120b
on NVIDIA NIM. NO magent pipeline, NO schema validation, NO multi-agent
specialist routing. Capture everything for the comparison report.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

import certifi
import httpx
import openai

API_KEY = os.environ["NVIDIA_API_KEY"]
BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "openai/gpt-oss-120b"

http = httpx.Client(verify=False, timeout=600.0)
client = openai.OpenAI(base_url=BASE_URL, api_key=API_KEY, http_client=http)

prompt = (
    "Build a small Python CLI todo app with add / list / done commands and "
    "JSON file persistence (path read from TODO_STORE_FILE env var). "
    "Output ALL the source files I need. Use any format you want."
)
print("=== RAW prompt ===")
print(prompt)
print(f"\n=== model: {MODEL} ===\n")

t0 = time.time()
resp = client.chat.completions.create(
    model=MODEL,
    max_tokens=4096,
    messages=[
        {"role": "system", "content": "You are a senior software engineer. Be direct and complete."},
        {"role": "user", "content": prompt},
    ],
)
dt = time.time() - t0
text = resp.choices[0].message.content or ""
usage = resp.usage

print(f"=== response in {dt:.1f}s ===")
print(f"  input_tokens={usage.prompt_tokens}, output_tokens={usage.completion_tokens}")
print(f"  total chars: {len(text)}")

# Persist
out_dir = Path("specs/_raw_baseline").resolve()
if out_dir.exists():
    shutil.rmtree(out_dir)
out_dir.mkdir(parents=True)
(out_dir / "raw_response.md").write_text(text, encoding="utf-8")
(out_dir / "metadata.json").write_text(json.dumps({
    "model": MODEL, "wall_seconds": dt,
    "input_tokens": usage.prompt_tokens,
    "output_tokens": usage.completion_tokens,
    "response_chars": len(text),
}, indent=2), encoding="utf-8")
print(f"\nresponse saved: {out_dir / 'raw_response.md'}")

# Crude parseability probe — count python code blocks; can we extract real
# files from this prose? Manual extraction follows.
import re
code_blocks = re.findall(r"```(?:python|py)?\n(.*?)```", text, re.DOTALL)
print(f"\n=== parseability metrics ===")
print(f"  python code blocks found: {len(code_blocks)}")
for i, blk in enumerate(code_blocks[:3]):
    print(f"  block {i+1}: {len(blk)}b, first line: {blk.splitlines()[0] if blk.splitlines() else '<empty>'!r}")

# Try to find file path hints in the prose
file_hints = re.findall(r"`?([\w./\-]+\.py)`?", text)
unique_hints = sorted(set(file_hints))
print(f"  file paths mentioned: {unique_hints[:10]}")

# Schema validation? No schema. We can only check if it's a valid Constitution
# (no, raw text isn't), valid FeatureSpec (no), etc. ALL artifact validations
# fail by definition because the response IS NOT structured.
print(f"\n=== schema validation against Phase 7 schemas ===")
from agents.spec_schemas import Constitution, FeatureSpec, ImplementationPlan, TaskList, ImplementationTrace
for cls in (Constitution, FeatureSpec, ImplementationPlan, TaskList, ImplementationTrace):
    try:
        cls.model_validate_json(text)
        print(f"  {cls.__name__}: PASS")
    except Exception:
        print(f"  {cls.__name__}: FAIL (expected — raw is unstructured)")

# Try to extract code blocks and run any tests they contain
print(f"\n=== extract + materialize files ===")
ws = out_dir / "workspace"
ws.mkdir(exist_ok=True)
extracted = 0
for blk in code_blocks:
    # Look for filename hint in first 3 lines
    lines = blk.splitlines()
    fname_hint = None
    for line in lines[:3]:
        m = re.match(r"^[#/\s]*([\w./\-]+\.py)", line.strip())
        if m:
            fname_hint = m.group(1)
            break
    if not fname_hint:
        continue
    target = ws / fname_hint
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(blk, encoding="utf-8")
    extracted += 1
    print(f"  wrote {fname_hint} ({len(blk)}b)")
print(f"  total files extracted: {extracted}")

# Are there ANY tests in there?
tests = list(ws.rglob("test_*.py")) + list(ws.rglob("*_test.py"))
print(f"  test files found: {len(tests)}")

# Traceability: does the response link any FR-IDs to commits / files?
fr_mentions = re.findall(r"FR-\d+", text)
print(f"  FR-### mentions: {len(set(fr_mentions))} unique ({sorted(set(fr_mentions))[:5]})")

print(f"\n=== summary saved to {out_dir} ===")
