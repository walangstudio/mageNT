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
3. Each body ends with a `## Team Context` block: `SendMessage` is always
   available regardless of the `tools:` allowlist, the task-ledger claim/
   complete protocol is mandatory, and a `shutdown_request` must be answered
   with a `shutdown_response` (see "Shutting down" below).
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

## Shutting down & cleanup

Agent-teams shutdown is a **two-phase handshake over `SendMessage`**, not
idleness:

1. The lead sends each teammate a `shutdown_request` carrying a `request_id`.
2. Each teammate MUST reply with a `shutdown_response` echoing the exact
   `request_id` — `approve: true` once its ledger task is `completed`, or
   `approve: false` with a one-line `reason` if it has unfinished in-scope
   work.
3. Only after every teammate has approved does the lead run cleanup /
   `TeamDelete` and remove `~/.claude/teams/<name>/`. Cleanup **fails** while
   any teammate is still active.

**Idle is not shut down.** A teammate with no open task is still a live
session; finishing a turn or replying in plain text is not acknowledgment. If
a teammate never returns a `shutdown_response`, the team can't be disbanded
cleanly — the `magent-team_lead` agent drives this handshake, and every
generated subagent's `## Team Context` block instructs teammates to answer.
The shipped preset cleanup prompts ask each teammate to confirm shutdown
before cleanup for this reason.

**Protocol messages are handled first.** The `## Team Context` block tells
every teammate that when a turn is woken by a `shutdown_request` *or* a
`plan_approval_request`, emitting the matching `_response` is that turn's only
required action — checked before any other work, ahead of the "no task = done"
instinct. `plan_approval_request` follows the same handshake as shutdown:
reply with a `plan_approval_response` echoing the `request_id`, `approve` true,
or false with `feedback`.

**Expected first-request miss + recovery.** In live testing a magent teammate
often idles on the *first* `shutdown_request` without answering — its
JSON-only persona treats "no open task" as "done". This is recovered, not
fatal: the lead immediately follows with a plain-text nudge containing the
literal payload to send —

```
You missed a shutdown_request. Send exactly: SendMessage to "<lead>" with
message {"type":"shutdown_response","request_id":"<that id>","approve":true}.
Do it now.
```

— and the teammate then emits a correct `shutdown_response`, the framework
reports `shutdown_approved` (request_id echoed) + `teammate_terminated`, and
`TeamDelete` succeeds. `magent-team_lead` performs this nudge automatically;
don't wait on an idle teammate after a shutdown_request — nudge it. The nudge
is **mandatory, not optional**: the lead must not report a teammate as
"parked" or unresponsive until it has sent the nudge and repeated it once. Only
after a teammate ignores two nudges does the lead escalate to the user, naming
the teammate and the outstanding `request_id`.

### Multiplexers & pane teardown (tmux, iTerm2, in-process)

A teammate's shutdown action is **the same on every backend** — it sends the
`shutdown_response` object, nothing more. Closing the window is the Claude Code
runtime's job, not mageNT's: mageNT ships no tmux/iTerm2 code and issues no
teardown shell command. The `shutdown_approved` the framework emits carries
`paneId` and `backendType`, which is what its teardown branches on
(verified live: on Windows both are `"in-process"`). So there is **no
per-multiplexer instruction for a teammate** — do not add one; the handshake is
backend-agnostic.

Which backend runs is set by `settings.json` `"teammateMode"`
(`"auto"` | `"in-process"` | `"tmux"`) or `--teammate-mode`. Claude Code
split-pane mode supports **tmux** (macOS/Linux) and **iTerm2** (macOS only, via
the [`it2` CLI](https://github.com/mkusaka/it2)); `"auto"` uses split panes only
when already inside a tmux session and **in-process** (no panes) otherwise.
**Windows has no tmux/iTerm2 — it is always in-process**, so panes never appear
and there is nothing to close.

Teardown by backend:

- **tmux** — framework runs `kill-pane`; the pane closes cleanly on a normal
  shutdown.
- **in-process** — no pane exists; the session just ends.
- **iTerm2** — **known upstream bug**
  ([claude-code#24385](https://github.com/anthropics/claude-code/issues/24385)):
  the framework reports `teammate_terminated` but never calls the iTerm2
  `async_close()`, so the pane lingers with a dead shell. mageNT cannot fix this
  from a prompt — it is in the runtime. A lingering iTerm2 pane **after a clean
  `teammate_terminated` is this bug, not an incomplete handshake**: close it
  manually, or run teams under tmux / in-process mode until it's fixed
  upstream. (Contrast: a pane that lingers with the teammate *still alive* is
  the idle-vs-shutdown miss above — fix that with the lead nudge.)

## Parallel dispatch playbook

Lessons from running 6 specialists in parallel on real backend work. These are
the LEAD's job — they can't be fixed in the teammate prompt.

- **Pre-create worktrees from the named ref you're on, not default-fresh.** The
  `Agent` tool's `isolation: "worktree"` defaults to `worktree.baseRef: "fresh"`,
  which branches from `origin/main`. If your work lives on a feature branch,
  either create the worktrees yourself —
  `git worktree add .claude/worktrees/<name> -b agent/<name> <feature-branch>`
  and pass the path in the briefing — or set `worktree.baseRef: "head"` in
  settings.json. Otherwise teammates branch from the wrong base.
- **Brief shared-file edits by line range, not "section name."** Two agents can
  safely share one file if you name the exact spans (e.g. "imports 15-26" vs
  "root handler 171-173"). Agents take "the X section" too liberally and
  collide.
- **Own the wire-up explicitly.** When a feature spans two files owned by two
  agents, neither owns the cross-cutting wire-up by default — so it silently
  doesn't happen (an added API never gets called). Assign one agent the wire-up
  step, or brief one agent with both files, or run an integration-verification
  pass after dispatch. This is the single biggest structural risk in parallel
  dispatch.
- **Brief "trace upstream/downstream first" for integration-sensitive tasks.**
  E.g. "before writing the cron, grep all `UPDATE <table>` statements and
  confirm which column the success path mutates." Agents respect their owned
  scope literally and skip cross-file research unless told to do it.
- **Run a code-review pass after parallel dispatch, before merge — mandatory.**
  Parallel-agent output is materially more defect-dense than single-author code
  (file-ownership scoping hides cross-cutting bugs; an agent that writes both
  impl and test can pin a bug as the spec). The review catches no-op wire-ups
  and integration races that no single teammate could see. Skipping it ships
  those.
- **Keep Sonnet as the default; reserve Opus selectively.** Per-agent Opus lifts
  first-pass correctness only marginally and costs ~5x; it does NOT fix the
  structural issues above (those are prompt/workflow, now handled by the team
  protocol block). Use the `staff-implementers` profile (Opus) only for
  cross-cutting refactors, security/PII/crypto, or perf-critical paths.

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
