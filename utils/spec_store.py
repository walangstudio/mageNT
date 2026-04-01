"""Spec store — read/write structured markdown spec files."""

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:50].strip("-")


def _parse_front_matter(content: str) -> tuple[dict, str]:
    """Return (metadata_dict, body) from a markdown file with YAML front-matter."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---", 3)
    if end == -1:
        return {}, content
    fm_block = content[3:end].strip()
    body = content[end + 4:].strip()
    meta: dict = {}
    for line in fm_block.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, body


class SpecStore:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _spec_dir(self, spec_id: str) -> Path:
        candidate = (self.base_dir / spec_id).resolve()
        if not str(candidate).startswith(str(self.base_dir)):
            raise ValueError(f"Invalid spec_id: '{spec_id}'")
        return candidate

    def create(
        self,
        spec_id: str,
        project_name: str,
        description: str,
        requirements: List[str],
    ) -> Path:
        spec_dir = self._spec_dir(spec_id)
        spec_dir.mkdir(parents=True, exist_ok=True)
        checklist = "\n".join(f"- [ ] {r}" for r in requirements)
        content = f"""---
spec_id: {spec_id}
project_name: {project_name}
created_at: {datetime.now(timezone.utc).isoformat()}
status: draft
---

# Requirements Spec: {project_name}

## Description
{description}

## Acceptance Checklist
{checklist}
"""
        path = spec_dir / "spec.md"
        path.write_text(content, encoding="utf-8")
        return path

    def load(self, spec_id: str) -> Dict[str, Any]:
        path = self._spec_dir(spec_id) / "spec.md"
        content = path.read_text(encoding="utf-8")
        meta, body = _parse_front_matter(content)
        return {"meta": meta, "body": body, "content": content, "path": str(path)}

    def exists(self, spec_id: str) -> bool:
        try:
            return (self._spec_dir(spec_id) / "spec.md").exists()
        except ValueError:
            return False

    def arch_spec_exists(self, spec_id: str) -> bool:
        try:
            return (self._spec_dir(spec_id) / "arch_spec.md").exists()
        except ValueError:
            return False

    def list_specs(self) -> List[Dict[str, Any]]:
        results = []
        for spec_dir in sorted(self.base_dir.iterdir()):
            spec_file = spec_dir / "spec.md"
            if spec_dir.is_dir() and spec_file.exists():
                try:
                    meta, _ = _parse_front_matter(spec_file.read_text(encoding="utf-8"))
                    if meta:  # skip corrupt/empty front-matter
                        results.append(meta)
                except Exception:
                    pass
        return results

    def save_arch_spec(self, spec_id: str, content: str) -> Path:
        path = self._spec_dir(spec_id) / "arch_spec.md"
        path.write_text(content, encoding="utf-8")
        return path

    def load_arch_spec(self, spec_id: str) -> Dict[str, Any]:
        path = self._spec_dir(spec_id) / "arch_spec.md"
        content = path.read_text(encoding="utf-8")
        meta, body = _parse_front_matter(content)
        return {"meta": meta, "body": body, "content": content, "path": str(path)}

    def save_phase_results(self, spec_id: str, phase: str, results: Dict[str, str]) -> Path:
        path = self._spec_dir(spec_id) / f"phase_{phase}_results.json"
        path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load_phase_results(self, spec_id: str, phase: str) -> Optional[Dict[str, str]]:
        path = self._spec_dir(spec_id) / f"phase_{phase}_results.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def load_all_phase_results(self, spec_id: str) -> Dict[str, str]:
        """Merge results from all saved phases into a single agent→result dict."""
        spec_dir = self._spec_dir(spec_id)
        combined: Dict[str, str] = {}
        for f in sorted(spec_dir.glob("phase_*_results.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                combined.update(data)
            except Exception:
                pass
        return combined

    # --- spec-kit compatible output ---

    def create_speckit(self, spec_id: str, project_name: str, spec_content: str) -> Path:
        """Write spec-kit formatted spec.md."""
        spec_dir = self._spec_dir(spec_id)
        spec_dir.mkdir(parents=True, exist_ok=True)
        path = spec_dir / "spec.md"
        path.write_text(spec_content, encoding="utf-8")
        return path

    def save_speckit_plan(self, spec_id: str, content: str) -> Path:
        """Write spec-kit formatted plan.md."""
        path = self._spec_dir(spec_id) / "plan.md"
        path.write_text(content, encoding="utf-8")
        return path

    def save_speckit_tasks(self, spec_id: str, tasks: List[Dict[str, Any]]) -> List[Path]:
        """Write individual task .md files into tasks/ subdirectory.

        Each task dict must have: name, files, prompt.
        Generates YAML frontmatter with name and files fields
        that borch's speckit::parse() can consume.
        """
        tasks_dir = self._spec_dir(spec_id) / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for i, task in enumerate(tasks):
            name = task.get("name", f"task-{i + 1:03d}")
            files = task.get("files", "")
            prompt = task.get("prompt", "")
            filename = f"T{i + 1:03d}-{name}.md"
            content = f"---\nname: {name}\nfiles: {files}\n---\n\n{prompt}\n"
            path = tasks_dir / filename
            path.write_text(content, encoding="utf-8")
            paths.append(path)
        return paths

    @staticmethod
    def make_spec_id(project_name: str) -> str:
        slug = _slugify(project_name)
        suffix = uuid.uuid4().hex[:8]
        return f"{slug}-{suffix}"
