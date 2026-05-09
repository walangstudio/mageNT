"""SHA-tracked manifest for safe upgrade and uninstall of generated dispatch files.

The generator writes ``.magent-manifest.json`` next to the agents/ and skills/
directories it created. Each entry records the SHA-256 of the file at write
time. On upgrade we re-render and overwrite only if the existing file's hash
still matches what we wrote. On uninstall we remove only files whose hash
still matches — anything the user edited is preserved.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Dict, Iterable, List, Optional, Tuple

MANIFEST_FILENAME = ".magent-manifest.json"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str) -> Optional[str]:
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def manifest_path(root: str) -> str:
    return os.path.join(root, MANIFEST_FILENAME)


def load(root: str) -> Dict[str, str]:
    p = manifest_path(root)
    if not os.path.isfile(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    files = data.get("files") if isinstance(data, dict) else None
    return files if isinstance(files, dict) else {}


def save(root: str, files: Dict[str, str]) -> None:
    p = manifest_path(root)
    os.makedirs(root, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "files": files}, f, indent=2, sort_keys=True)


def write_file(
    root: str,
    rel_path: str,
    content: str,
    manifest: Dict[str, str],
    force: bool = False,
    dry_run: bool = False,
) -> Tuple[str, str]:
    """Write content to ``root/rel_path`` and update the manifest.

    Returns a ``(action, message)`` tuple where action is one of
    ``"created"``, ``"updated"``, ``"skipped-user-edit"``, ``"skipped-same"``.
    """
    abs_path = os.path.join(root, rel_path)
    new_hash = sha256_text(content)
    existing_hash = sha256_file(abs_path)
    recorded_hash = manifest.get(rel_path)

    if existing_hash is None:
        action = "created"
    elif existing_hash == new_hash:
        action = "skipped-same"
    elif recorded_hash and existing_hash != recorded_hash and not force:
        return "skipped-user-edit", (
            f"{rel_path}: file changed since last install, not overwriting "
            f"(use --force to override)"
        )
    else:
        action = "updated"

    if action != "skipped-same" and not dry_run:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    manifest[rel_path] = new_hash
    return action, f"{rel_path}: {action}"


def remove_managed(
    root: str,
    manifest: Dict[str, str],
    force: bool = False,
    dry_run: bool = False,
) -> List[Tuple[str, str]]:
    """Remove all files in the manifest whose on-disk hash still matches."""
    results: List[Tuple[str, str]] = []
    for rel_path, recorded_hash in list(manifest.items()):
        abs_path = os.path.join(root, rel_path)
        existing_hash = sha256_file(abs_path)
        if existing_hash is None:
            results.append(("missing", f"{rel_path}: already gone"))
            manifest.pop(rel_path, None)
            continue
        if existing_hash != recorded_hash and not force:
            results.append((
                "kept-user-edit",
                f"{rel_path}: edited locally, kept (use --force to remove)",
            ))
            continue
        if not dry_run:
            try:
                os.remove(abs_path)
            except OSError as e:
                results.append(("error", f"{rel_path}: {e}"))
                continue
            parent = os.path.dirname(abs_path)
            if parent and parent != root and os.path.isdir(parent):
                try:
                    if not os.listdir(parent):
                        os.rmdir(parent)
                except OSError:
                    pass
        manifest.pop(rel_path, None)
        results.append(("removed", f"{rel_path}: removed"))

    if not dry_run:
        if manifest:
            save(root, manifest)
        else:
            mp = manifest_path(root)
            if os.path.isfile(mp):
                try:
                    os.remove(mp)
                except OSError:
                    pass
    return results


def summarize(actions: Iterable[Tuple[str, str]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for action, _ in actions:
        counts[action] = counts.get(action, 0) + 1
    return counts
