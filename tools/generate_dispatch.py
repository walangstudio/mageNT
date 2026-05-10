"""Emit Claude Code subagent and skill markdown from mageNT agent classes.

Source of truth stays in the Python agent classes; this script just renders
those into the markdown shapes Claude Code expects, using the mode mapping
in ``config/dispatch.yaml``.

Typical use::

    python tools/generate_dispatch.py --target ~/.claude
    python tools/generate_dispatch.py --target tools/_sandbox --dry-run
    python tools/generate_dispatch.py --target ~/.claude --uninstall

The script never touches MCP config — that's the installer's job.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import yaml  # noqa: E402  (after sys.path manipulation)

from tools import dispatch_manifest as manifest  # noqa: E402

CONFIG_PATH = os.path.join(REPO_ROOT, "config", "dispatch.yaml")
MAX_DESCRIPTION_LEN = 1024


def load_config(path: str = CONFIG_PATH) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_agent_classes() -> Dict[str, type]:
    import server  # type: ignore
    return dict(server.AGENT_CLASSES)


def load_skill_classes() -> Dict[str, type]:
    from skills.scaffold.react import ScaffoldReact
    from skills.scaffold.nextjs import ScaffoldNextJS
    from skills.scaffold.fastapi import ScaffoldFastAPI
    from skills.scaffold.express import ScaffoldExpress
    from skills.analysis.debug import DebugCode
    from skills.analysis.error_analyzer import AnalyzeError
    from skills.testing.run_tests import RunTests
    from skills.testing.generate_tests import GenerateTests
    from skills.version.check_versions import CheckVersions
    from skills.security.security_scan import SecurityScan

    return {
        "scaffold_react": ScaffoldReact,
        "scaffold_nextjs": ScaffoldNextJS,
        "scaffold_fastapi": ScaffoldFastAPI,
        "scaffold_express": ScaffoldExpress,
        "debug_code": DebugCode,
        "analyze_error": AnalyzeError,
        "run_tests": RunTests,
        "generate_tests": GenerateTests,
        "check_versions": CheckVersions,
        "security_scan": SecurityScan,
    }


def _instantiate_agent(cls: type) -> Any:
    spec = (cls.__doc__ or "").strip().splitlines()[0] if cls.__doc__ else ""
    return cls({"expertise_level": "principal", "specialization": spec})


def _truncate(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _yaml_list(items: List[str]) -> str:
    if not items:
        return "[]"
    return "[" + ", ".join(items) + "]"


def render_subagent(name: str, cls: type, spec: Dict[str, Any]) -> str:
    agent = _instantiate_agent(cls)
    role = agent.role
    use_cases = agent.use_cases or []
    triggers = "; ".join(use_cases[:3]) or role
    stance = getattr(agent, "opinionated_stance", "") or ""
    description = _truncate(
        f"{role} — use proactively for {triggers}. {stance}".strip(),
        MAX_DESCRIPTION_LEN,
    )
    tools = spec.get("tools") or ["Read", "Grep", "Glob", "Bash"]
    model = spec.get("model", "sonnet")

    body = agent.get_system_prompt()

    front = [
        "---",
        f"name: magent-{name}",
        f"description: {description}",
        f"tools: {_yaml_list(tools)}",
        f"model: {model}",
        "---",
    ]
    return "\n".join(front) + "\n\n" + body.rstrip() + "\n"


def render_skill_from_agent(name: str, cls: type, spec: Dict[str, Any]) -> str:
    agent = _instantiate_agent(cls)
    description = _truncate(
        f"{agent.role} advisory skill. " + "; ".join(agent.use_cases[:3] or [agent.role]),
        MAX_DESCRIPTION_LEN,
    )
    tools = spec.get("tools") or ["Read", "Grep", "Glob"]

    front = [
        "---",
        f"name: magent-{name}",
        f"description: {description}",
        f"allowed-tools: {_yaml_list(tools)}",
        "---",
    ]

    body_lines: List[str] = [f"# {agent.role}", ""]
    if getattr(agent, "opinionated_stance", ""):
        body_lines += [agent.opinionated_stance.strip(), ""]
    body_lines += ["## When to Activate"]
    body_lines += [f"- {u}" for u in (agent.use_cases or [f"{agent.role} consultation"])]
    body_lines += [""]
    process = list(getattr(agent, "process_steps", []) or [])
    if not process:
        process = [f"Apply: {p}" for p in (agent.best_practices or [])[:6]]
    if process:
        body_lines += ["## Workflow"]
        for i, step in enumerate(process, 1):
            body_lines.append(f"{i}. {step}")
        body_lines.append("")
    output_format = getattr(agent, "output_format", "")
    if output_format:
        body_lines += ["## Output Format", output_format.strip(), ""]
    if agent.best_practices:
        body_lines += ["## Heuristics"]
        body_lines += [f"- {bp}" for bp in agent.best_practices]
        body_lines.append("")

    return "\n".join(front) + "\n\n" + "\n".join(body_lines).rstrip() + "\n"


def render_skill_from_skill(name: str, cls: type, spec: Dict[str, Any]) -> str:
    skill = cls()
    description = _truncate(skill.description, MAX_DESCRIPTION_LEN)
    tools = spec.get("tools") or list(skill.allowed_tools)

    front = [
        "---",
        f"name: magent-{name}",
        f"description: {description}",
        f"allowed-tools: {_yaml_list(tools)}",
        "---",
    ]

    body_lines: List[str] = [f"# {skill.name.replace('_', ' ').title()}", ""]
    body_lines += [skill.description, ""]

    when = skill.when_to_activate
    if when:
        body_lines += ["## When to Activate"]
        body_lines += [f"- {w}" for w in when]
        body_lines.append("")
    elif skill.parameters:
        body_lines += [
            "## When to Activate",
            f"- User invokes `{skill.slash_command}` or asks for a {skill.category} action.",
            "",
        ]

    workflow = skill.workflow
    if workflow:
        body_lines += ["## Workflow"]
        for i, step in enumerate(workflow, 1):
            body_lines.append(f"{i}. {step}")
        body_lines.append("")

    if skill.parameters:
        body_lines += ["## Parameters"]
        for p in skill.parameters:
            req = " (required)" if p.get("required") else ""
            body_lines.append(
                f"- `{p['name']}` ({p.get('type', 'string')}){req}: "
                f"{p.get('description', '')}"
            )
        body_lines.append("")

    if skill.output_schema:
        body_lines += ["## Output Format", skill.output_schema.strip(), ""]

    body_lines += [
        "## Slash Command",
        f"`{skill.slash_command}`",
        "",
    ]

    return "\n".join(front) + "\n\n" + "\n".join(body_lines).rstrip() + "\n"


def render_skill_passthrough(name: str, spec: Dict[str, Any]) -> str:
    """Render a SKILL.md for a dispatch.yaml entry that has no Python class.

    Used by Phase 7 magent_* skills that wrap an MCP tool 1:1. The skill body
    embeds the description, when-to-activate, inputs, and produces fields from
    dispatch.yaml so a Claude Code user opening the skill sees a real workflow
    doc — not a generic stub.
    """
    description = _truncate(
        spec.get("description")
        or f"Invokes the `{name}` MCP tool. See magent docs for the full schema.",
        MAX_DESCRIPTION_LEN,
    )
    tools = spec.get("tools") or ["Read", "Bash"]
    pretty = name.replace("_", " ").title()
    slash_name = name.replace("_", "-")
    # Frontmatter name must match the on-disk skill dir; if dispatch.yaml entry
    # already prefixes with magent_, don't double-prefix.
    fm_name = slash_name if slash_name.startswith("magent-") else f"magent-{slash_name}"
    front = [
        "---",
        f"name: {fm_name}",
        f"description: {description}",
        f"allowed-tools: {_yaml_list(tools)}",
        "---",
    ]
    body = [
        f"# {pretty}",
        "",
        description,
        "",
    ]
    when_text = spec.get("when")
    if when_text:
        body += ["## When to Activate", f"- {when_text}", ""]
    else:
        body += [
            "## When to Activate",
            f"- User invokes `/{slash_name}` or asks for a {spec.get('category', 'pipeline')} action.",
            "",
        ]
    inputs = spec.get("inputs") or []
    if inputs:
        body += ["## Inputs"]
        for line in inputs:
            body.append(f"- {line}")
        body.append("")
    produces = spec.get("produces")
    if produces:
        body += ["## Produces", produces, ""]
    body += [
        "## Workflow",
        f"1. Invoke the `{name}` MCP tool with the inputs above.",
        "2. Read the validated artifact path + JSON summary the tool returns.",
        "3. If the tool returns `phase_gate`, the upstream phase is missing or invalid — run that phase first and retry.",
        "4. If the tool returns `escalation`, the agent failed schema validation 3x in a row — inspect `cost.json` for context and decide whether to re-prompt or hand off.",
        "",
        "## Slash Command",
        f"`/{slash_name}`",
        "",
    ]
    return "\n".join(front) + "\n\n" + "\n".join(body).rstrip() + "\n"


def plan_files(
    config: Dict[str, Any],
    only_modes: Optional[List[str]] = None,
) -> List[Tuple[str, str, str]]:
    """Return a list of ``(rel_path, content, kind)`` tuples to write."""
    agents_cfg = (config.get("agents") or {})
    skills_cfg = (config.get("skills") or {})
    agent_classes = load_agent_classes()
    skill_classes = load_skill_classes()

    files: List[Tuple[str, str, str]] = []

    for name, cls in agent_classes.items():
        spec = agents_cfg.get(name) or {"mode": "mcp_only"}
        mode = spec.get("mode", "mcp_only")
        if only_modes and mode not in only_modes:
            continue
        if mode == "subagent":
            files.append((
                f"agents/magent-{name}.md",
                render_subagent(name, cls, spec),
                "subagent",
            ))
        elif mode == "skill":
            files.append((
                f"skills/magent-{name}/SKILL.md",
                render_skill_from_agent(name, cls, spec),
                "skill",
            ))

    for name, cls in skill_classes.items():
        spec = skills_cfg.get(name) or {"mode": "skill"}
        mode = spec.get("mode", "skill")
        if only_modes and mode not in only_modes:
            continue
        if mode == "skill":
            files.append((
                f"skills/magent-{name}/SKILL.md",
                render_skill_from_skill(name, cls, spec),
                "skill",
            ))

    # Pass-through skills: dispatch.yaml entries with no Python class.
    # Used for Phase 7 magent_* MCP-tool wrappers so Claude Code gets a
    # slash-command surface without needing one BaseSkill subclass per tool.
    rendered_skill_names = {n for n in skill_classes}
    rendered_agent_names = {n for n in agent_classes}
    for name, spec in skills_cfg.items():
        if name in rendered_skill_names or name in rendered_agent_names:
            continue
        mode = spec.get("mode", "skill")
        if only_modes and mode not in only_modes:
            continue
        if mode == "skill":
            # Strip the redundant `magent_` prefix if the entry already has it
            # (e.g. magent_spec → just `spec`); otherwise prepend `magent-`.
            slug = name.replace("_", "-")
            if slug.startswith("magent-"):
                dirname = slug
            else:
                dirname = f"magent-{slug}"
            files.append((
                f"skills/{dirname}/SKILL.md",
                render_skill_passthrough(name, spec),
                "skill",
            ))

    files.sort(key=lambda x: x[0])
    return files


def cmd_generate(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    target = os.path.abspath(os.path.expanduser(args.target))
    only_modes: Optional[List[str]] = None
    if args.profile == "subagents":
        only_modes = ["subagent"]
    elif args.profile == "skills":
        only_modes = ["skill"]

    plan = plan_files(config, only_modes=only_modes)

    existing = manifest.load(target)
    fresh: Dict[str, str] = {}
    actions: List[Tuple[str, str]] = []

    for rel_path, content, _kind in plan:
        action, message = manifest.write_file(
            target, rel_path, content,
            existing,
            force=args.force,
            dry_run=args.dry_run,
        )
        actions.append((action, message))
        # `existing` is mutated in place when a file is written; carry forward
        # any path that was successfully (re)recorded.
        if rel_path in existing:
            fresh[rel_path] = existing[rel_path]

    if not args.dry_run:
        manifest.save(target, fresh)

    counts = manifest.summarize(actions)
    print(f"Target: {target}")
    print(f"Profile: {args.profile or 'full'}  Mode: generate  Dry-run: {args.dry_run}")
    for _action, message in actions:
        print(f"  {message}")
    print("Summary:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "(no files)")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    target = os.path.abspath(os.path.expanduser(args.target))
    existing = manifest.load(target)
    if not existing:
        print(f"No manifest at {target}; nothing to remove.")
        return 0
    actions = manifest.remove_managed(
        target,
        existing,
        force=args.force,
        dry_run=args.dry_run,
    )
    counts = manifest.summarize(actions)
    print(f"Target: {target}  Mode: uninstall  Dry-run: {args.dry_run}")
    for _action, message in actions:
        print(f"  {message}")
    print("Summary:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "(empty)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--target", required=True,
        help="Directory that contains agents/ and skills/ (e.g. ~/.claude or .claude).",
    )
    p.add_argument(
        "--config", default=CONFIG_PATH,
        help="Path to dispatch.yaml (default: config/dispatch.yaml).",
    )
    p.add_argument("--profile", choices=["full", "subagents", "skills"], default="full")
    p.add_argument("--dry-run", action="store_true",
                   help="Print actions without writing or deleting.")
    p.add_argument("--force", action="store_true",
                   help="Overwrite user-edited files / remove user-edited files on uninstall.")
    p.add_argument("--uninstall", action="store_true",
                   help="Remove files tracked in the manifest.")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.uninstall:
        return cmd_uninstall(args)
    return cmd_generate(args)


if __name__ == "__main__":
    sys.exit(main())
