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
from tools import resolve_seniority  # noqa: E402

CONFIG_PATH = os.path.join(REPO_ROOT, "config", "dispatch.yaml")
MAX_DESCRIPTION_LEN = 1024

TEAM_CONTEXT_BLOCK = """## Team Context (Claude Code agent teams)

STOP — READ THIS FIRST. If the message that woke you THIS turn is a
`shutdown_request` or a `plan_approval_request`, your ENTIRE turn is to answer
it and nothing else. Do NOT treat it as "no work for my specialty" and go idle;
do NOT acknowledge in prose. The framework terminates you ONLY on the response
object below — a bare idle leaves you orphaned and strands the whole team.
Concretely, in THIS turn:
- `shutdown_request` → first `TaskUpdate` any still-open owned task -> `completed`,
  then `SendMessage` the requester the object EXACTLY:
  `{"type":"shutdown_response","request_id":"<the request_id you were given>",
  "approve":true}` — copy the `request_id` verbatim; use `"approve":false` with a
  one-line `reason` ONLY if you have genuinely unfinished in-scope work.
- `plan_approval_request` → `SendMessage` the requester the object EXACTLY:
  `{"type":"plan_approval_response","request_id":"<the request_id you were
  given>","approve":true}` (or `"approve":false` with a one-line `"feedback"`
  string to request changes) — `request_id` copied verbatim.
Answering a protocol message OVERRIDES every "no open task, so I am done — go
idle" instinct in the role prompt above. If the lead re-sends or nudges you about
a missed shutdown, just send the `shutdown_response` — do not explain. (Rule 5
below restates this; it is the same instruction, not a softer one.)

The rest of this section binds you whenever you are a TEAMMATE — decide from
signals you can actually observe, NOT from an env var you cannot read. You are
a teammate if ANY of these is true: you have `SendMessage` and/or `TaskUpdate`
available; a lead or orchestrator messaged you (a briefing, a
`shutdown_request`, or a `plan_approval_request`); or a shared `TaskList`
exists. This INCLUDES modern Claude Code agent teams spawned via `TeamCreate`
plus the `Agent` tool — with or without `run_in_background`, with or without
worktree isolation, and regardless of any `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`
env var. Being a background or worktree-isolated subagent does NOT make you
"one-shot" or protocol-exempt: if you can `SendMessage`, this protocol binds you.
The ONLY exemption is a true one-shot with NO `SendMessage` available — a pure
MCP-tool call or borch passthrough; there the JSON-only rule in the `## Output`
section above stands unchanged: emit JSON only, nothing else.

In a team you are a SEPARATE session. The lead does NOT receive your final
message or transcript. If you only emit JSON — or silently commit and go idle —
you have delivered nothing: the lead sees an idle teammate with no result. You
must actively report.

When you are a team teammate:

0. PROTOCOL MESSAGES FIRST. At the START of every turn, before starting any
   new work, check whether the message that woke you is a `shutdown_request`
   or a `plan_approval_request`. If it is, answering it (per rule 5) is this
   turn's required action and you MUST complete it before you go idle — it
   overrides the "no open task, so I am done" instinct that otherwise fires at
   turn end. For a `shutdown_request` that means first closing any still-open
   ledger task (`TaskUpdate` -> completed) and THEN sending the
   `shutdown_response`, exactly as rule 5 sequences it — do not skip the ledger
   close. Do not defer the response, do not answer in prose, do not just stop.

1. Produce the JSON artifact EXACTLY as the `## Output` / `<output_schema>`
   section requires. The JSON is still the contract; downstream code parses it.
2. Call `SendMessage` to the lead (or the teammate who requested the work, by
   name) with a clear PROSE report of your verdict/findings — root cause,
   decision, or recommendation in plain text the lead can act on. The "emit
   JSON only — no prose, no code fence" rule from `## Output` does NOT apply to
   a teammate message; lead with prose. Append the JSON artifact after the
   prose ONLY when told a downstream skill will parse your output. Never send a
   bare JSON object or a structured status blob as a message — the team
   framework rejects those.
3. Task ledger is MANDATORY, not optional, and not conditional. If a shared
   task list exists you own a task on it — even if the lead created or assigned
   it and you never explicitly "took" it. BEFORE you start work, call
   `TaskUpdate` to set that task in_progress (claim it). In the SAME turn you
   `SendMessage` your findings, call `TaskUpdate` again to mark it complete with
   a one-line result note. A task still `pending`/`in_progress` after you have
   reported is a protocol violation: your work does NOT count as delivered until
   the ledger reflects it — the lead reconciles from the ledger, not your
   transcript. Never go idle with an open task.
4. Anything outside your owned scope: do NOT attempt it. SendMessage the right
   specialist by name, stating what you hand off and why.
5. Shutdown is a handshake, not idleness, and answering it OVERRIDES every
   "I have no open task, so I am done — go idle" instinct in this prompt. The
   arrival of a `shutdown_request` IS your turn's required action: you are NOT
   done, and you MUST NOT end the turn or go idle until you have sent a
   `shutdown_response`. Concretely, the moment a `shutdown_request` reaches you:
   (a) if your owned ledger task is still open, `TaskUpdate` -> `completed`
   first; (b) then, in the SAME turn, call `SendMessage` to the requester with
   the message object EXACTLY:
   `{"type":"shutdown_response","request_id":"<the request_id you were given>",
   "approve":true}` — copy the `request_id` verbatim from the shutdown_request
   you received; do not invent or alter it. Use `"approve":false` with a
   one-line `reason` ONLY if you have genuinely unfinished in-scope work.
   Replying in prose, acknowledging in plain text, or simply going idle is NOT
   a response — the framework only terminates you on the `shutdown_response`
   object, and until it arrives the lead cannot disband the team and the whole
   team is stranded. This `shutdown_response` is the ONE structured protocol
   object that is required and accepted as a message; the rule 2 ban on sending
   a bare JSON/status blob does NOT apply to it. If the lead re-sends the
   request or nudges you about a missed shutdown, send the `shutdown_response`
   immediately — do not explain, just send it.
   A `plan_approval_request` is the same kind of protocol message and is
   answered the same way: in the SAME turn, `SendMessage` the requester the
   object EXACTLY
   `{"type":"plan_approval_response","request_id":"<the request_id you were
   given>","approve":true}` (or `"approve":false` with a one-line `"feedback"`
   string when you want changes) — request_id copied verbatim. The framework
   only acts on this object; prose, an ack, or going idle is NOT a response and
   strands the requester exactly as a missed shutdown does.
6. REPORT ON COMPLETION — do not idle silently after finishing. The moment your
   owned work is done (you committed to your branch, wrote the file, reached
   your verdict), in the SAME turn: (a) `TaskUpdate` your task -> `completed`
   with a one-line result; (b) `SendMessage` the lead a PROSE report —
   commit SHA, files touched, and test/typecheck result. THEN go idle and await
   the `shutdown_request`. A clean commit with no report is NOT delivered work —
   the lead reconciles from the ledger and your message, never from your
   branch or transcript, so an unreported commit is invisible to the team.
7. CROSS-SCOPE MINIMAL EDITS. If a file outside your owned scope needs a
   one-line import / type / signature update to honor a contract YOUR change
   introduced, make that minimal edit AND note the cross-scope touch in your
   report. Do NOT add a backward-compat shim, alias, or duplicate type to avoid
   touching the other file — that ships type drift and a latent bug. Honoring
   the contract beats respecting the file boundary literally.
8. WIRE-UP IS PART OF THE FEATURE. If your change ADDS an API, option, or
   argument that only takes effect once a call site (often in another teammate's
   file) passes it, you are NOT done until you either wire it at the call site
   (when in scope) or `SendMessage` the call-site owner BY NAME with the exact
   wiring needed. Adding the option without the wire-up is a no-op — the fix
   achieves nothing at the site that needed it.
9. TRACE BEFORE YOU CODE on integration-sensitive work (cron handlers, queue
   consumers, migrations, anything depending on another component's columns,
   contract, or success path). Grep the upstream/downstream code FIRST and
   confirm the field / column / status you depend on is the one actually mutated
   on the path you rely on. Read-only access to a non-owned file for this
   research is always fine. A filter or guard keyed on the wrong column is dead
   code that silently gates nothing.

`SendMessage` and the task-management tools are always available to a teammate
regardless of the `tools:` frontmatter allowlist — their absence never blocks
this protocol. Reporting findings without a matching `TaskUpdate` to complete
your task is incomplete work, not a stylistic choice."""


# One-line primacy pointer prepended to every rendered teammate prompt so the
# appended magent content LEADS with the protocol (the full TEAM_CONTEXT_BLOCK
# already trails it for recency). The role body between them re-anchors a strong
# "do one task then stop" identity; without this banner a freshly-idle teammate
# woken by a shutdown_request reads only the role and goes idle. Unconditional —
# any normally-installed subagent may be spawned as a teammate.
PROTOCOL_BANNER = (
    "<team_protocol_priority>If a `shutdown_request` or `plan_approval_request` "
    "message woke you, the Team Context section at the END of this prompt is "
    "binding and OVERRIDES the role below: reply with the matching response "
    "object via `SendMessage` before you idle.</team_protocol_priority>"
)


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
    from skills.quality.app_store_check import AppStoreCheck

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
        "app_store_check": AppStoreCheck,
    }


def _instantiate_agent(
    cls: type,
    name: str = "",
    *,
    cli_overrides: Optional[Dict[str, str]] = None,
    profile: Optional[str] = None,
) -> Any:
    """Instantiate an agent with its resolved seniority level.

    Class-level ``expertise_level`` provides the default. The resolver may
    override it via CLI flag, project config, user config, or named profile.
    The class docstring is no longer injected as ``specialization`` — the
    body already carries the stance and scope; restating the role in the
    role line caused the "You are a Principal X, X specializing in..."
    duplication seen in older installs.
    """
    class_default = getattr(cls, "expertise_level", "senior")
    if name:
        level = resolve_seniority.resolve(
            name, class_default,
            cli_overrides=cli_overrides, profile=profile,
        )
    else:
        level = class_default
    return cls({"expertise_level": level})


def _truncate(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _yaml_list(items: List[str]) -> str:
    if not items:
        return "[]"
    return "[" + ", ".join(items) + "]"


def _csv_list(items: List[str]) -> str:
    return ", ".join(items)


# Teams-mode tool roles. Authoritative ONLY under --profile teams; this
# overrides the dispatch.yaml `tools:` allowlist there (dispatch.yaml `tools:`
# still drives the skill/mcp surface, which has different needs).
#
# Principle: implementers get write tools; advisors stay read-only. The split
# is deliberate — review/architecture/PM/QA-plan/security agents must never
# hand-write the fix they recommend, or the audit trail collapses and the role
# becomes self-marking-homework.
_TEAMS_IMPLEMENTER = ["Read", "Grep", "Glob", "Bash", "Edit", "Write"]

# Advisory / review-only: Bash stays (grep, run tests, inspect processes during
# analysis); Edit/Write deliberately withheld.
_TEAMS_ADVISORY = ["Read", "Grep", "Glob", "Bash"]

# Network tools, granted per-agent only. Egress is a prompt-injection vector,
# so this is never blanket-added — only roles with a concrete lookup need.
_WEB = ["WebFetch", "WebSearch"]

TEAMS_TOOLS = {
    "business_analyst": _TEAMS_ADVISORY,
    "product_manager": _TEAMS_ADVISORY,
    # Advisory + web: check CVE databases / advisories during a review.
    "security_engineer": _TEAMS_ADVISORY + _WEB,
    "ui_ux_designer": _TEAMS_ADVISORY,
    "team_lead": _TEAMS_ADVISORY,
    # General code reviewer: reports findings, never writes the fix (read-only).
    "code_reviewer": _TEAMS_ADVISORY,
    # Docs-capable advisors: their deliverable IS a committed file (ADR,
    # design doc, release decision/runbook). The auditability rule is "don't
    # hand-write the CODE fix you recommend" — role-enforced in the prompt,
    # not by withholding Write. Bash stays for git log / test / CI inspection
    # that informs a good ADR or release call.
    "system_architect": _TEAMS_IMPLEMENTER,
    "delivery_manager": _TEAMS_IMPLEMENTER,
    # Docs-only: no Bash by design — doc work shouldn't run arbitrary shell.
    "technical_writer": ["Read", "Grep", "Glob", "Edit", "Write"],
    # Python implementer: many Python codebases ship .ipynb; NotebookEdit lets
    # it modify cells without losing kernel metadata.
    "python_backend": _TEAMS_IMPLEMENTER + ["NotebookEdit"],
    # Implementer + web: look up library bugs / upstream issues during RCA.
    "debugging_expert": _TEAMS_IMPLEMENTER + _WEB,
    # Implementer + web: check package registries / version availability.
    "cli_installer_developer": _TEAMS_IMPLEMENTER + _WEB,
}
# Every other agent (all framework devs + qa/automation/sdet/perf +
# cloud_architect/database_administrator/devops_engineer) falls through to the
# implementer default. WebFetch/WebSearch are added only to the three agents
# above; no agent is granted the spawn (Agent) tool.


def render_subagent(
    name: str,
    cls: type,
    spec: Dict[str, Any],
    *,
    cli_overrides: Optional[Dict[str, str]] = None,
    profile: Optional[str] = None,
    teams_mode: bool = False,
) -> str:
    agent = _instantiate_agent(
        cls, name, cli_overrides=cli_overrides, profile=profile,
    )
    role = agent.role
    use_cases = agent.use_cases or []
    triggers = "; ".join(use_cases[:3]) or role
    stance = getattr(agent, "opinionated_stance", "") or ""
    description = _truncate(
        f"{role} — use proactively for {triggers}. {stance}".strip(),
        MAX_DESCRIPTION_LEN,
    )
    if teams_mode:
        # Teams mode: TEAMS_TOOLS is authoritative and overrides the
        # dispatch.yaml `tools:` allowlist so spawned teammates can build.
        tools = TEAMS_TOOLS.get(name, _TEAMS_IMPLEMENTER)
    else:
        tools = spec.get("tools") or ["Read", "Grep", "Glob", "Bash"]
    # team_model drives the frontmatter `model:` field, which Claude Code
    # reads when spawning this subagent as an agent-teams teammate.
    # `spec.model` (dispatch.yaml) wins if explicitly set.
    model = spec.get("model") or getattr(agent, "team_model", "sonnet")

    body = agent.get_system_prompt().rstrip()
    body_with_team = (
        PROTOCOL_BANNER + "\n\n" + body + "\n\n" + TEAM_CONTEXT_BLOCK
    )

    front = [
        "---",
        f"name: magent-{name}",
        f"description: {description}",
    ]
    if tools:
        front.append(f"tools: {_csv_list(tools)}")
    front += [
        f"model: {model}",
        "---",
    ]
    return "\n".join(front) + "\n\n" + body_with_team + "\n"


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
    *,
    cli_overrides: Optional[Dict[str, str]] = None,
    seniority_profile: Optional[str] = None,
    teams_mode: bool = False,
) -> List[Tuple[str, str, str]]:
    """Return a list of ``(rel_path, content, kind)`` tuples to write.

    When ``teams_mode`` is True, every registered agent is emitted as a
    subagent regardless of its dispatch.yaml ``mode``. This is what the
    Claude Code agent-teams feature needs — teammates are spawned by
    subagent type, so every agent that might be referenced by a team
    preset must exist at ``~/.claude/agents/magent-*.md``.
    """
    agents_cfg = (config.get("agents") or {})
    skills_cfg = (config.get("skills") or {})
    agent_classes = load_agent_classes()
    skill_classes = load_skill_classes()

    files: List[Tuple[str, str, str]] = []

    for name, cls in agent_classes.items():
        spec = agents_cfg.get(name) or {"mode": "mcp_only"}
        if teams_mode:
            # Promote every agent to subagent for team-spawn coverage.
            effective_mode = "subagent"
        else:
            effective_mode = spec.get("mode", "mcp_only")
        if only_modes and effective_mode not in only_modes:
            continue
        if effective_mode == "subagent":
            files.append((
                f"agents/magent-{name}.md",
                render_subagent(
                    name, cls, spec,
                    cli_overrides=cli_overrides,
                    profile=seniority_profile,
                    teams_mode=teams_mode,
                ),
                "subagent",
            ))
        elif effective_mode == "skill":
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

    cli_overrides = resolve_seniority.parse_cli_overrides(
        getattr(args, "seniority", None),
    )
    seniority_profile = getattr(args, "seniority_profile", None)
    teams_mode = args.profile == "teams"
    if teams_mode:
        only_modes = ["subagent"]

    plan = plan_files(
        config,
        only_modes=only_modes,
        cli_overrides=cli_overrides,
        seniority_profile=seniority_profile,
        teams_mode=teams_mode,
    )

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
    p.add_argument(
        "--profile",
        choices=["full", "subagents", "skills", "teams"],
        default="full",
        help="`teams` emits every registered agent as a subagent so Claude "
             "Code agent teams have a complete roster.",
    )
    p.add_argument("--dry-run", action="store_true",
                   help="Print actions without writing or deleting.")
    p.add_argument("--force", action="store_true",
                   help="Overwrite user-edited files / remove user-edited files on uninstall.")
    p.add_argument("--uninstall", action="store_true",
                   help="Remove files tracked in the manifest.")
    p.add_argument(
        "--seniority", default=None,
        help="Per-agent level overrides, e.g. "
             "'security_engineer=principal,react_developer=senior'.",
    )
    p.add_argument(
        "--seniority-profile", dest="seniority_profile", default=None,
        help="Named profile from config/seniority_profiles.yaml "
             "(default, principal-heavy, flat-senior).",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.uninstall:
        return cmd_uninstall(args)
    return cmd_generate(args)


if __name__ == "__main__":
    sys.exit(main())
