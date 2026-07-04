"""Deterministic Mermaid diagram rendering from an ImplementationPlan.

C4-style container diagram (``flowchart LR`` — renders on GitHub, unlike
mermaid's experimental C4 syntax) plus an ERD from the plan's data model.
No LLM involved: same plan in, same text out.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, List


def _label(text: str, limit: int = 60) -> str:
    clean = text.replace('"', "'").strip()
    return clean[:limit] + ("…" if len(clean) > limit else "")


def render_container_mmd(plan: Any) -> str:
    lines = ["flowchart LR", '    client((Client))']
    comp_ids = {c.name: f"C{i}" for i, c in enumerate(plan.components)}
    lines.append(f'    subgraph system["{_label(plan.spec_id)}"]')
    for c in plan.components:
        lines.append(f'        {comp_ids[c.name]}["{_label(c.name)}<br/>{_label(c.responsibility)}"]')
    lines.append("    end")
    for ep in plan.api_contracts:
        target = None
        ep_frs = set(ep.fr_ids)
        for c in plan.components:
            if ep_frs and ep_frs & set(c.owns_fr_ids):
                target = comp_ids[c.name]
                break
        if target is None and plan.components:
            target = comp_ids[plan.components[0].name]
        if target:
            lines.append(f'    client -->|"{ep.method} {_label(ep.path, 40)}"| {target}')
    if plan.tech_stack.database:
        lines.append(f'    db[("{_label(plan.tech_stack.database)}")]')
        for c in plan.components:
            lines.append(f"    {comp_ids[c.name]} --> db")
    return "\n".join(lines) + "\n"


_REL_PATTERNS = [
    (re.compile(r"(?i)\bhas many\b\s+(\w+)"), "||--o{"),
    (re.compile(r"(?i)\bmany[- ]to[- ]many\b\s+(?:with\s+)?(\w+)"), "}o--o{"),
    (re.compile(r"(?i)\bhas one\b\s+(\w+)"), "||--||"),
    (re.compile(r"(?i)\bbelongs to\b\s+(\w+)"), "}o--||"),
    (re.compile(r"(?i)\breferences\b\s+(\w+)"), "}o--||"),
]

_NAME_SAN = re.compile(r"[^A-Za-z0-9_]")


def _sanitize(name: str) -> str:
    return _NAME_SAN.sub("_", name.strip()) or "unnamed"


def render_erd_mmd(plan: Any) -> str:
    lines = ["erDiagram"]
    for entity in plan.data_model:
        ename = _sanitize(entity.name)
        lines.append(f"    {ename} {{")
        for fname, ftype in entity.fields.items():
            first = re.match(r"[A-Za-z0-9_]+", ftype.strip())
            lines.append(f"        {first.group(0) if first else 'string'} {_sanitize(fname)}")
        lines.append("    }")
    for entity in plan.data_model:
        ename = _sanitize(entity.name)
        for rel in entity.relationships:
            for pattern, cardinality in _REL_PATTERNS:
                m = pattern.search(rel)
                if m:
                    lines.append(
                        f'    {ename} {cardinality} {_sanitize(m.group(1))} : "{_label(rel, 40)}"')
                    break
            else:
                lines.append(f"    %% {ename}: {_label(rel, 80)}")
    return "\n".join(lines) + "\n"


def write_diagrams(spec_dir: Path, plan: Any) -> List[Path]:
    """Write container.mmd (+ erd.mmd when there is a data model). Returns paths."""
    diagrams_dir = Path(spec_dir) / "diagrams"
    diagrams_dir.mkdir(parents=True, exist_ok=True)
    written = []
    container = diagrams_dir / "container.mmd"
    container.write_text(render_container_mmd(plan), encoding="utf-8")
    written.append(container)
    if plan.data_model:
        erd = diagrams_dir / "erd.mmd"
        erd.write_text(render_erd_mmd(plan), encoding="utf-8")
        written.append(erd)
    return written
