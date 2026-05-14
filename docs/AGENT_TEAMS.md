# mageNT × Claude Code Agent Teams

Claude Code shipped an experimental [agent-teams feature](https://code.claude.com/docs/en/agent-teams)
that spawns separate Claude Code instances as parallel **teammates**, coordinated
via a shared task list and inter-agent mailbox. mageNT exposes 36 specialist
agents plus a `magent-team_lead` coordinator as subagents, so any of them
can be spawned as a teammate.

This guide covers the install flow, four shipped team presets, lifecycle
hooks, and the known limits.

## Prerequisites

- Claude Code **v2.1.32+** (`claude --version`)
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `~/.claude/settings.json`
  (the installer prompts; or `python tools/enable_teams.py`)
- mageNT installed in `--mode subagents` or `--mode hybrid`
- For full preset coverage, use `--profile teams` (37 subagents incl.
  `magent-team_lead`) instead of `--profile subagents` (11 review/audit
  roles only)

Quick readiness check:

```sh
magent doctor
```

Sample output:

```
agents installed: 37 at /home/me/.claude/agents
agent-teams flag:  enabled in /home/me/.claude/settings.json
claude version:    2.1.141 (Claude Code) -- OK

preset roster check:
  audit-team: OK
  spec-team: OK
  release-team: OK
  stack-build-team: OK
```

## Installing for teams

```sh
./install.sh -c claude --mode subagents --profile teams --enable-teams
```

What that does:

1. Renders all 37 agent classes (incl. `magent-team_lead`) to
   `~/.claude/agents/magent-*.md` via `tools/generate_dispatch.py`.
2. Each subagent's `model:` frontmatter field is set from the agent's
   `team_model` property (Principal/Staff → `opus`; Senior/specialist →
   `sonnet`).
3. Each body ends with a `## Team Context` block reminding the teammate that
   `SendMessage` is always available regardless of the `tools:` allowlist.
4. Sets `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in
   `~/.claude/settings.json` (idempotent JSON merge).

To override per-agent levels:

```sh
magent generate --target ~/.claude --profile teams \
                --seniority security_engineer=principal,react_developer=senior
```

Named profiles live in `config/seniority_profiles.yaml`
(`default`, `principal-heavy`, `flat-senior`); add your own there.

## Shipped team presets

Four copy-pasteable lead prompts in `examples/teams/`:

| Preset | Roster |
|---|---|
| [audit-team](../examples/teams/audit-team.md) | delivery_manager + security_engineer + performance_engineer + qa_engineer |
| [spec-team](../examples/teams/spec-team.md) | business_analyst + system_architect + product_manager |
| [release-team](../examples/teams/release-team.md) | qa_engineer + devops_engineer + delivery_manager |
| [stack-build-team](../examples/teams/stack-build-team.md) | system_architect + react_developer + nodejs_backend + database_administrator |

Paste the prompt from one of those files into a fresh Claude Code session;
the lead spawns the named teammates with explicit per-teammate scope.

A `magent-team_lead` subagent is also installed; you can spawn it explicitly
when you want a single coordinator that picks the roster for you:

```
Spawn a teammate using the magent-team_lead agent type. Ask it to audit PR #42.
```

## Lifecycle hooks

Two example hooks in `hooks/teams/`. Both safe to enable globally — they
no-op when their preconditions aren't met.

Paste into `~/.claude/settings.json` (replace `<REPO>` with the absolute path
to your mageNT checkout):

```json
{
  "hooks": {
    "TaskCompleted": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "python <REPO>/hooks/teams/task_completed_validate.py"
          }
        ]
      }
    ],
    "TeammateIdle": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "python <REPO>/hooks/teams/teammate_idle_summary.py"
          }
        ]
      }
    ]
  }
}
```

- `task_completed_validate` — runs `magent validate <specs-dir>` when a
  teammate marks a spec task complete. Exit 2 rejects the completion and
  surfaces the validator errors to the teammate.
- `teammate_idle_summary` — appends a one-line status to
  `specs/active/team_log.md` whenever a teammate goes idle. Gives the lead
  one file to scan when synthesizing.

## Caveats

- **Teammates do not inherit `skills` or `mcpServers`** from the subagent
  definition (per the agent-teams docs). They get the `tools:` allowlist and
  the body content. mageNT's bodies are self-contained — no MCP/skill
  references — so this is fine. Don't add MCP-tool instructions to the
  bodies if you customize.
- **One team per lead.** Teammates cannot spawn nested teams.
- **No session resumption** for in-process teammates (`/resume` / `/rewind`
  don't restore them).
- **Experimental.** The flag may be renamed or removed. Pin Claude Code
  version if you're scripting this.

## Customizing

- **Add a new agent** — drop a `BaseAgent` subclass in `agents/<domain>/`,
  set `expertise_level`, register in `server.AGENT_CLASSES`, add a
  `subagent` entry to `config/dispatch.yaml`, regenerate.
- **Change a level** — edit the `expertise_level` class attribute, or
  override via `~/.magent/seniority.yaml` (per-machine) or
  `./magent.seniority.yaml` (per-project), or pass `--seniority` to
  `magent generate`.
- **New preset** — add a markdown file to `examples/teams/`, then add the
  roster to `magent_cli/__main__.py::_TEAM_PRESETS` so `magent doctor`
  validates it.
