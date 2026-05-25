# mageNT

![version](https://img.shields.io/badge/version-0.7.3-blue)
![python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-compatible-blueviolet)
![platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![license](https://img.shields.io/badge/license-MIT-green)

Give Claude a team of specialist developers through MCP. Works with Claude Desktop, Claude Code, or any MCP client.

## What's this?

Ever wish Claude had deep expertise in specific areas? That's what mageNT does. Instead of getting generic advice, you can consult actual specialists:

- Need requirements? Talk to the Business Analyst
- Building a React app? Get the React Developer
- Designing an API? Ask the API Developer

Think of it like having 45 specialists on standby — Principals, Staff, and Senior engineers picked per role, plus a team-lead coordinator — each with their own specialty. You can also run a full spec-driven development cycle — from requirements to parallel implementation to delivery audit — with a single tool call per step, or spawn a parallel team of teammates in Claude Code (v2.1.32+).

## What's new in 0.7

Claude Code agent-teams support (experimental). A new `--profile teams` install emits every agent — including a coordinating `magent-team_lead` — as a subagent under `~/.claude/agents/`, so any of them is spawnable as a parallel teammate via Claude Code's [agent-teams feature](https://code.claude.com/docs/en/agent-teams). Four shipped presets (audit / spec / release / stack-build) in [`examples/teams/`](examples/teams/). Two lifecycle hooks in [`hooks/teams/`](hooks/teams/) wire `magent validate` into `TaskCompleted` and append teammate-idle status to `specs/active/team_log.md`. New `magent doctor` CLI reports install count, env flag, Claude Code version, and per-preset roster completeness.

Per-agent seniority is now configurable. Each agent has a baked `expertise_level` (Principal / Staff / Senior / specialist) overridable via `~/.magent/seniority.yaml`, `./magent.seniority.yaml`, `--seniority-profile`, or `--seniority` CLI flag. `team_model` derives from level (Principal/Staff → Opus, Senior/specialist → Sonnet) and lands in the generated `model:` frontmatter for teammate spawning.

Plus a renderer fix: subagent bodies no longer open with the stale "You are a Principal X, X specializing in..." duplication; the role line now reads cleanly as "You are a Staff Security Engineer." See [`docs/AGENT_TEAMS.md`](docs/AGENT_TEAMS.md).

## What's new in 0.6

A complete spec-driven pipeline that takes an idea to a passing-tests, audited, release-ready artifact: `magent_constitution → magent_spec → magent_clarify → magent_plan → magent_tasks → magent_implement → magent_audit → magent_release`. Every artifact is a typed Pydantic schema (`agents/spec_schemas.py`); a validator CLI (`tools/validate_spec.py`) cross-checks FR-IDs, refuses unresolved `[NEEDS CLARIFICATION]` items, and confirms every Task's `failing_test_path` exists on disk. Plus brownfield deltas (`magent_spec_delta`), per-phase cost tracking, stuck-loop escalation, and a `PRE_COMMIT` hook that auto-prepends FR-IDs to commit messages. Slash-command UX via 9 new Claude Code skills.

See [Building from Idea to Release](#building-from-idea-to-release) below.

## What's new in 0.5

The prompt template was rewritten end-to-end. Each agent now ships an opinionated stance, an explicit scope/defer-to map, decision heuristics, anti-examples, and a Pydantic JSON-Schema as the response contract. Claude Code users can install agents as **subagents** + **skills** alongside (or instead of) the MCP tool path.

A multi-model eval (DeepSeek v4-pro, GPT-OSS-120b, Nemotron-3-Super 120b) on 8 hard tasks shows v2 prompts win **24 / 0 / 0** pairwise vs vanilla baselines and lift parseability from **0%** to **100%**. Full report: [`tests/prompt_eval/results/report-v2c.md`](tests/prompt_eval/results/report-v2c.md).

## Quick Start

Run the installer:

**Linux / macOS / Git Bash (Windows):**
```bash
cd mageNT
./install.sh                              # Claude Desktop
./install.sh -c claude                    # Claude Code (workspace-local)
./install.sh -c claude --global           # Claude Code (global user config)
./install.sh -c cursor                    # Cursor (workspace-local)
./install.sh -c cursor --global           # Cursor (global)
./install.sh -c windsurf                  # Windsurf (global only)
./install.sh -c vscode                    # VS Code (.vscode/mcp.json)
./install.sh -c gemini                    # Gemini CLI (workspace-local)
./install.sh -c gemini --global           # Gemini CLI (global)
./install.sh -c codex                     # OpenAI Codex CLI (workspace-local)
./install.sh -c codex --global            # OpenAI Codex CLI (global)
./install.sh -c zed                       # Zed (global)
./install.sh -c kilo                      # Kilo Code
./install.sh -c opencode                  # OpenCode (workspace-local)
./install.sh -c opencode --global         # OpenCode (global)
./install.sh -c goose                     # Goose
./install.sh -c all                       # all detected clients
```

**Windows (Command Prompt / PowerShell):**
```bat
cd mageNT
install.bat                               REM Claude Desktop
install.bat -c claude                     REM Claude Code (workspace-local)
install.bat -c claude --global            REM Claude Code (global user config)
install.bat -c cursor                     REM Cursor (workspace-local)
install.bat -c cursor --global            REM Cursor (global)
install.bat -c windsurf                   REM Windsurf (global only)
install.bat -c vscode                     REM VS Code (.vscode/mcp.json)
install.bat -c gemini                     REM Gemini CLI (workspace-local)
install.bat -c gemini --global            REM Gemini CLI (global)
install.bat -c codex                      REM OpenAI Codex CLI (workspace-local)
install.bat -c codex --global             REM OpenAI Codex CLI (global)
install.bat -c zed                        REM Zed (global)
install.bat -c kilo                       REM Kilo Code
install.bat -c opencode                   REM OpenCode (workspace-local)
install.bat -c opencode --global          REM OpenCode (global)
install.bat -c goose                      REM Goose
install.bat -c all                        REM all detected clients
```

That's it. The installer handles everything — creates a venv, installs deps, configures your MCP client, runs tests.

Then just restart your client and try:
```
List the available agents
```

## Supported MCP Clients

| Client | `-c TYPE` | Config written | Notes |
|--------|-----------|----------------|-------|
| Claude Desktop | `claudedesktop` | OS-specific `claude_desktop_config.json` | Restart required |
| Claude Code | `claude` | `.mcp.json` (workspace) or `~/.claude.json` (global) | Use `--global` for user scope |
| Cursor | `cursor` | `.cursor/mcp.json` or `~/.cursor/mcp.json` (global) | Use `--global` for global |
| Windsurf | `windsurf` | `~/.codeium/windsurf/mcp_config.json` | Global only |
| VS Code | `vscode` | `.vscode/mcp.json` | Workspace-local; global via VS Code settings UI |
| Gemini CLI | `gemini` | `.gemini/settings.json` or `~/.gemini/settings.json` (global) | Use `--global` for global |
| Codex CLI | `codex` | `.codex/config.toml` or `~/.codex/config.toml` (global) | TOML; use `--global` for global |
| Zed | `zed` | `~/.config/zed/settings.json` | Global only |
| Kilo Code | `kilo` | `.kilocode/mcp.json` | Workspace-local only |
| OpenCode | `opencode` | `opencode.json` / `~/.config/opencode/opencode.json` | Use `--global` for global |
| Goose | `goose` | `~/.config/goose/config.yaml` | Global only |
| pi.dev | `pidev` | n/a | Prints manual instructions; no auto-config |
| All above | `all` | All detected existing configs | Skips clients not yet installed |

### pi.dev manual setup

pi.dev uses a TypeScript extension API rather than standard MCP JSON. Add a minimal bridge extension:

```typescript
// ~/.pi/extensions/magent-bridge.ts
import { Extension } from "@pi-dev/sdk";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

export default class MagentBridge extends Extension {
  name = "magent";

  async activate() {
    const transport = new StdioClientTransport({
      command: "/path/to/mageNT/.venv/bin/python",
      args: ["/path/to/mageNT/server.py"],
    });
    const client = new Client({ name: "magent-bridge", version: "1.0.0" }, {});
    await client.connect(transport);
    this.registerMcpClient(client);
  }
}
```

Register it in `~/.pi/agent/settings.json`:
```json
{
  "extensions": ["~/.pi/extensions/magent-bridge.ts"]
}
```

### Installer Flags

```
  -c, --client TYPE   claudedesktop, claude, cursor, windsurf, vscode, gemini, codex,
                      zed, kilo, opencode, goose, pidev, all  (default: claudedesktop)
  -f, --force         Skip prompts, overwrite existing config
  -u, --uninstall     Remove from MCP client config
      --upgrade       Upgrade deps and reconfigure (alias: --update)
      --status        Show where this server is currently installed
      --global        Write to global config (claude, cursor, gemini, codex, opencode)
      --skip-test     Skip server validation
      --mode MODE     auto|mcp|skills|subagents|hybrid (default: auto;
                      claude→hybrid, others→mcp)
      --profile P     full|minimal|skills|subagents|teams (default: full)
      --enable-teams  Set CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 in
                      ~/.claude/settings.json (Claude Code agent teams)
      --no-enable-teams
                      Skip the agent-teams prompt
      --scope S       ask|user|project (Claude Code only; default: ask)
      --agents-dir D  Override target agents/ directory (Claude Code only)
      --skills-dir D  Override target skills/ directory (Claude Code only)
      --regenerate    Re-run the dispatch generator before installing
      --dry-run       Print actions without writing
  -h, --help          Show this help
```

### Subagents + Skills (Claude Code only)

On Claude Code, the default `--mode auto` resolves to **`hybrid`**: review/audit personas (security_engineer, system_architect, delivery_manager, etc.) install as native subagents under `~/.claude/agents/magent-*.md`; scaffold helpers (react, nextjs, fastapi, express) and lightweight workflow tools install as skills under `~/.claude/skills/magent-*/SKILL.md`; the MCP server stays installed for stateful tools (workflows, specs, recall, parallel orchestration). Other clients still get the standard MCP-only install.

Per-agent dispatch lives in [`config/dispatch.yaml`](config/dispatch.yaml). Markdown is generated from the Python agent classes by [`tools/generate_dispatch.py`](tools/generate_dispatch.py); a SHA-tracked manifest at `~/.claude/.magent-manifest.json` lets `--upgrade` and `--uninstall` skip files you've edited by hand.

#### `--mode` vs `--profile`

`--mode` decides **which delivery channels** mageNT uses; `--profile` decides **which files** get rendered into the subagent/skill channels. They compose.

| `--mode` | MCP server registered | Subagent/skill files written |
|---|---|---|
| `mcp` | ✅ | ❌ |
| `subagents` | ❌ | ✅ (filtered by `--profile`) |
| `skills` | ❌ | ✅ (filtered by `--profile`) |
| `hybrid` (default for `-c claude`) | ✅ | ✅ (filtered by `--profile`) |

`--mode subagents` and `--mode skills` are the same code path — both invoke the dispatch generator without registering MCP. Pick whichever name reads better; use `--profile` to constrain the output.

| `--profile` | What it emits |
|---|---|
| `full` (default) | Both subagents AND skills per dispatch.yaml |
| `subagents` | Only the 15 agents marked `subagent` in dispatch.yaml |
| `skills` | Only the 4 agents marked `skill` + the 15 scaffold/test/debug/quality skills |
| `teams` | All 45 agents as subagents (for agent-teams use) |

#### What you lose by skipping MCP

If you install with `--mode subagents` or `--mode skills` (no MCP), you keep all 45 subagents and the standalone scaffold/test/debug/quality skills, but you lose:

- The full **spec pipeline**: `magent_constitution → magent_spec → magent_clarify → magent_plan → magent_tasks → magent_implement → magent_audit → magent_release`. The `/magent-spec` etc. slash-command wrappers exist as skill files but their bodies invoke MCP tools — without MCP they're dead pointers.
- **`run_parallel_agents`** (concurrent agent orchestration with skill-affinity auto-selection)
- **`recall`** (cross-conversation memory)
- **Workflows** (`tdd`, etc.)
- **`consult_<agent>`** MCP tools (subagents cover the same agents via a different invocation path, so this is just stylistic)

For pure agent-teams use, dropping MCP is fine. For the spec-driven pipeline or parallel orchestration, keep `--mode hybrid`.

```bash
./install.sh -c claude                       # auto → hybrid (subagents + skills + MCP)
./install.sh -c claude --mode mcp            # MCP only (no subagent/skill files)
./install.sh -c claude --mode subagents --profile teams --enable-teams
                                             # Pure agent-teams setup, no MCP
./install.sh -c claude --mode hybrid --profile teams --enable-teams
                                             # Everything + agent teams (recommended)
./install.sh -c claude --scope project       # write to <workspace>/.claude/ instead of ~/.claude/
./install.sh -c claude --regenerate          # re-render markdown before install
./install.sh -c claude --dry-run             # preview actions without writing
```

### Agent teams support (experimental)

Claude Code v2.1.32+ has an experimental [agent-teams feature](https://code.claude.com/docs/en/agent-teams) that spawns separate Claude Code instances as parallel teammates. mageNT installs every agent (including a coordinating `magent-team_lead`) as a subagent so it's spawnable as a teammate:

```bash
./install.sh -c claude --mode subagents --profile teams --enable-teams
magent doctor                                 # readiness check
```

Four preset prompts in [`examples/teams/`](examples/teams/) cover audit, spec, release, and stack-build flows. See [`docs/AGENT_TEAMS.md`](docs/AGENT_TEAMS.md) for the full guide and lifecycle hooks.

### Checking install status

```bash
./install.sh --status
```

Scans all known config paths and prints a table showing which clients have mageNT registered.

### Updating

Pull the latest source first (or re-download and extract), then:

```bash
./install.sh --upgrade                    # upgrade deps + merge new agents into config
./install.sh --upgrade -c all             # also reconfigure all clients
./install.sh --upgrade -c claude          # upgrade + reconfigure Claude Code MCP path
```

`--update` is an alias for `--upgrade`.

Re-running the installer when already on the latest version exits cleanly with "Nothing to do."
Use `-f` to force reinstall, or `--upgrade -c claude` to reconfigure MCP client paths.

## Manual Setup

If you want to do it yourself:

```bash
cd mageNT
pip install -r requirements.txt
python server.py  # test it works, then Ctrl+C
```

Now add mageNT to your MCP client config (use absolute paths).

Most clients use the same `mcpServers` JSON — add this block to the config file for your client:

```json
{
  "mcpServers": {
    "magent": {
      "command": "/absolute/path/to/mageNT/.venv/bin/python",
      "args": ["/absolute/path/to/mageNT/server.py"]
    }
  }
}
```

| Client | Config file |
|--------|-------------|
| Claude Desktop | `%APPDATA%\Claude\claude_desktop_config.json` (Win) · `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) · `~/.config/Claude/claude_desktop_config.json` (Linux) |
| Claude Code | `.mcp.json` (workspace) or `~/.claude.json` (global) |
| Cursor | `.cursor/mcp.json` (workspace) or `~/.cursor/mcp.json` (global) |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| Gemini CLI | `.gemini/settings.json` (workspace) or `~/.gemini/settings.json` (global) |
| Kilo Code | `.kilocode/mcp.json` |

**Claude Code global (CLI):**
```bash
claude mcp add --scope user magent -- /absolute/path/to/mageNT/.venv/bin/python /absolute/path/to/mageNT/server.py
```

**Clients with different config format** — use the same `command`/`args` values, different structure:

| Client | Config file | Key difference |
|--------|-------------|----------------|
| VS Code | `.vscode/mcp.json` | Top-level key is `servers` (not `mcpServers`), add `"type": "stdio"` |
| Zed | `~/.config/zed/settings.json` | Top-level key is `context_servers`, command is nested: `{ "path": ..., "args": ..., "env": {} }` |
| OpenAI Codex | `.codex/config.toml` | TOML format: `[mcp_servers.magent]`, `command = "/path/to/.venv/bin/python /path/to/server.py"` |
| OpenCode | `opencode.json` or `~/.config/opencode/opencode.json` | Top-level key is `mcp` (not `mcpServers`) |
| Goose | `~/.config/goose/config.yaml` | YAML format: under `extensions`, uses `cmd`/`args`/`type: stdio`/`enabled: true` |

On Windows, use `C:\absolute\path\to\mageNT\.venv\Scripts\python.exe` for the command. Restart the client after editing any config.

## How to Use

Just talk to Claude normally:

```
I need to build user authentication - what's the best approach?
```

```
Can you review this React component for performance issues?
```

```
Start a full_stack_web workflow for a todo app
```

Claude knows when to pull in specialists automatically. Or you can request specific agents:

```
Consult the Security Engineer about this auth code
```

## Who's on the Team

39 agents across different areas. Each has a baked seniority level (Principal / Staff / Senior / specialist) that drives both the system-prompt role line and — in Claude Code agent teams — the `model:` selection (Principal/Staff → Opus, Senior/specialist → Sonnet).

| What they do | Who's available |
|----------|--------|
| Coordination | Team Lead (Principal — agent-teams coordinator) |
| Business stuff | Business Analyst, Product Manager (Principal), Delivery Manager (Principal) |
| Architecture & Design | System Architect (Principal), UI/UX Designer |
| Frontend | React, Next.js, Vue.js, Svelte devs |
| Backend | Node.js, Python, Java, Go, .NET, Rust, API, Integration specialists |
| Infrastructure | Database Administrator (Staff), DevOps (Staff), Cloud Architect (Principal) |
| Quality & Security | Security Engineer (Staff), Performance Engineer (Staff), SDET (Staff), QA Engineer, Automation QA, Debugging Expert |
| Mobile | Flutter, React Native, Android (Kotlin/Java), iOS (Swift/Obj-C), Mobile Dev |
| Other | Technical Writer, PHP, TUI, CLI/Installer, Full-Stack Dev |

## Spec-Driven Development

A structured flow for building new projects or features from scratch:

```
create_spec → create_arch_spec → run_parallel_agents → audit_spec
```

**1. Create a requirements spec**
```
Create a spec for a blog platform with user auth, post CRUD, and comments
```
Returns a `spec_id`. Spec stored to `specs/{spec_id}/spec.md`.

**2. Generate architecture**
```
Create an arch spec for spec_id: blog-platform-a1b2c3d4
```
System Architect produces tech stack, component design, API contracts, and data models.

**3. Run agents in parallel**
```
Run parallel agents for spec_id: blog-platform-a1b2c3d4, phase: build
```
Agents are auto-selected from the arch spec using keyword matching. All run concurrently. Results are saved automatically.

```
Run parallel agents for spec_id: blog-platform-a1b2c3d4, phase: qa
```
QA Engineer and Security Engineer review the architecture for risks.

**4. Audit against spec**
```
Audit spec: blog-platform-a1b2c3d4
```
Delivery Manager checks every acceptance checklist item — `MET`, `PARTIAL`, or `MISSING` — and returns a go/no-go decision.

When starting any workflow or spec, mageNT will ask if you'd like to follow a **TDD cycle** instead. It's optional.

## Skill Tools

10 skills are available as direct MCP tools alongside the agent consultation tools:

| Tool | What it does |
|------|-------------|
| `skill_debug_code` | Structured debugging guidance |
| `skill_analyze_error` | Error/exception root cause analysis |
| `skill_scaffold_react` | React + Vite project scaffold |
| `skill_scaffold_nextjs` | Next.js App Router scaffold |
| `skill_scaffold_fastapi` | FastAPI + Pydantic scaffold |
| `skill_scaffold_express` | Express.js scaffold |
| `skill_security_scan` | OWASP-aligned security checklist |
| `skill_generate_tests` | Test generation guidance |
| `skill_run_tests` | Test runner guidance |
| `skill_check_versions` | Dependency version and compatibility check |

Skills are also auto-invoked during `run_parallel_agents` based on the arch spec content.

## Code Quality Tools

There's also a rules engine that checks for common issues:

- Security problems (secrets in code, SQL injection, XSS)
- Style violations
- Performance antipatterns (N+1 queries, etc)
- Git stuff (bad commit messages, missing .gitignore)

Plus automation hooks:
- Pre-commit checks
- Code edit validation
- Security scans

Just ask Claude:
```
Check this code for issues: [paste code]
```

## Customizing

Edit `config.yaml` to tune agents:

```yaml
agents:
  react_developer:
    enabled: true
    expertise_level: "senior"   # principal | staff | senior | "" (no level word)
    specialization: "React 18, TypeScript, Tailwind"
```

Seniority can also be overridden without editing class code:

- `~/.magent/seniority.yaml` (per-machine) or `./magent.seniority.yaml` (per-repo): `{security_engineer: principal, react_developer: staff}`
- `magent generate --seniority security_engineer=principal,react_developer=staff`
- `magent generate --seniority-profile principal-heavy` (presets in [`config/seniority_profiles.yaml`](config/seniority_profiles.yaml))

The resolved level bakes into the generated subagent markdown at install time — no runtime lookup.

## Prompt Template (v2)

Each agent's system prompt is assembled by [`utils/prompt_builder.py`](utils/prompt_builder.py) from typed fields on the agent class. The structure (top to bottom):

- `<role>` — XML-tagged for prompt-cache stability; opens with the opinionated stance.
- `Filters:` — single-line shared rule set (deduped from per-agent boilerplate).
- `Domain:` — one-line capability hint derived from `capability_tags`.
- `## Scope` — `Own:` and `Defer:` lists. Out-of-scope requests must name the right specialist by name.
- `## Process` — numbered procedure.
- `## Heuristics` — decision rules.
- `## Output` — prose template OR a compact JSON-Schema snippet derived from the agent's `output_schema_class` (a Pydantic model).
- `## Escalation` — stop conditions.
- `## Anti-patterns` — `Do NOT ...` lines and a `Never emit:` phrase list.

Pydantic schemas live in [`agents/schemas.py`](agents/schemas.py): `SecurityReport`, `ADR`, `ReleaseAudit`, `DebugReport`, `PerfHypothesisReport`, `IndexAuditReport`, `TestPlan`. Adding `output_schema_class` to a new agent makes its responses parser-validatable end-to-end.

## Building from Idea to Release

The Phase 7 pipeline takes a one-line idea to a release-ready PR through eight schema-validated phases. Each phase routes to one or more specialist agents, validates the output against a Pydantic model, and refuses to advance if upstream artifacts are missing or invalid.

```
magent_constitution   delivery_manager + system_architect (parallel)
        ↓
magent_spec           business_analyst   → FeatureSpec (FR-### + RFC 2119 + G/W/T)
        ↓
magent_clarify        business_analyst   → ClarificationLog
        ↓
magent_plan           system_architect + database_administrator + cloud_architect
        ↓
magent_tasks          sdet + qa_engineer → TaskList (with auto-generated failing tests)
        ↓
magent_implement      per-task developer agents → ImplementationTrace
        ↓
magent_audit          delivery_manager + security_engineer + performance_engineer + qa_engineer
        ↓
magent_release        delivery_manager → ReleaseAudit (GO / NO-GO / GO-WITH-CONDITIONS)
```

**Validators that competitors only enforce by convention:**

- Tautological `THEN` clauses (`feature works as specified`) are rejected at schema time.
- Every Functional Requirement must contain its declared RFC 2119 verb (`MUST`, `SHOULD`, `MAY`, ...).
- `magent_plan` refuses to run if any `[NEEDS CLARIFICATION]` item is open on the spec.
- `magent_implement` refuses to run if any task's `failing_test_path` is absent on disk.
- `magent validate <spec-id>` cross-references FR-IDs across spec / tasks / implementation_trace.

**Capability comparison vs the leaders (May 2026):**

| Capability | Spec Kit | OpenSpec | GSD | mageNT 0.6 |
|---|---|---|---|---|
| FR-### IDs + RFC 2119 verbs | yes | yes | partial | **schema-validated** |
| Given/When/Then with falsifiable conditions | template | template | partial | **schema rejects tautology** |
| `[NEEDS CLARIFICATION]` blockers | yes | no | no | **typed, gates downstream** |
| Validator CLI | `/speckit.analyze` | `openspec validate` | partial | **`magent validate`** |
| Delta / brownfield specs | no | **killer feature** | no | **`magent_spec_delta`** |
| Constitution / project principles | yes | no | partial | **`magent_constitution`** |
| Tasks file with `[P]` parallel-safe + file paths | yes | implied | partial | **`Task` schema requires both** |
| Scenario → failing test derivation | implied | implied | no | **automatic, refuses to advance** |
| Multi-agent specialization at every phase | no | no | no | **yes (the structural moat)** |
| Pydantic schema as wire contract | no | partial | no | **every artifact** |
| FR-ID → commit traceability via hook | no | no | partial | **`PRE_COMMIT` hook** |
| Cost / token tracking per phase | no | no | yes | **`specs/<id>/cost.json`** |
| Stuck-loop detection + auto-escalate | no | no | yes | **3-attempt budget** |
| Cross-spec semantic memory | no | no | session-only | **mememo (persistent embeddings)** |
| Slash commands (Claude Code) | yes | yes | yes | **9 new skills** |
| MCP tool surface (every other client) | no | no | no | **9 new tools** |

**Quick start (against an empty project directory):**

```text
> magent_constitution project_name=todo-cli intent="A CLI todo app with add/list/done"
> magent_spec   spec_id=todo-cli-abc123 idea="add/list/done with persistent storage"
> magent_clarify spec_id=todo-cli-abc123
> magent_plan   spec_id=todo-cli-abc123
> magent_tasks  spec_id=todo-cli-abc123 project_root=.
> magent_implement spec_id=todo-cli-abc123
> magent_audit  spec_id=todo-cli-abc123
> magent_release spec_id=todo-cli-abc123
```

Or invoke any phase via slash command on Claude Code: `/magent-spec`, `/magent-plan`, `/magent-tasks`, etc.

Validate a spec at any time:

```bash
python tools/validate_spec.py <spec-id>     # exit 0 on pass, 1 on first failure
```

**Legacy spec tools** (`create_spec`, `create_arch_spec`, `run_parallel_agents`, `audit_spec`) still work and are kept for backwards compatibility, marked `[deprecated]` in their tool descriptions.

## Eval Harness

[`tests/prompt_eval/`](tests/prompt_eval/) compares prompt variants on a fixed task suite. The harness scores each response on a 7-dimension rubric (opinionatedness, scope_discipline, output_structure, conciseness, actionability, **parseability**, **template_adherence**) judged by a configurable LLM, and validates every response against the agent's Pydantic schema.

```bash
# OpenAI-compatible endpoint (e.g. NVIDIA NIM); runs the matrix and writes results JSON.
python tests/prompt_eval/run_matrix.py \
  --models openai/gpt-oss-120b deepseek-ai/deepseek-v4-pro \
  --tasks 9 10 11 12 13 14 15 16 \
  --conditions new baseline \
  --validate-schema \
  --out tests/prompt_eval/results/matrix.json

# Combine result files into a side-by-side markdown report.
python tests/prompt_eval/build_report.py \
  --inputs tests/prompt_eval/results/matrix.json \
  --out tests/prompt_eval/results/report.md
```

Latest hard-task report: [`results/report-v2c.md`](tests/prompt_eval/results/report-v2c.md). v2 magent prompts hit **24/24 pairwise wins** and **100% parseable** vs **0% parseable** for vanilla baselines.

## Workflows

Pre-built workflows coordinate multiple agents:

**Full lifecycle:**
- `new_system` - Greenfield project, all phases (requirements → design → dev → test → docs → deployment → sign-off)
- `add_feature` - Add a feature to an existing system with full quality gates
- `bug_fix` - Diagnose, fix, and regression-test a bug
- `full_audit` - Comprehensive health check of an existing system

**Focused workflows:**
- `full_stack_web` - Full web app (frontend + backend + database)
- `api_service` - API design and implementation
- `frontend_app` - UI/UX focused
- `tdd` - Test-driven development (red → green → refactor cycle)

Start one like:
```
Start the full_stack_web workflow for a blog platform
```

## Making Your Own Agents

Drop a new file in `agents/`:

```python
from agents.base import BaseAgent

class MyAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "my_agent"

    @property
    def role(self) -> str:
        return "My Specialist"

    # implement the rest...
```

Register it in `server.py` and add to `config.yaml`.

## Common Issues

**Agents not showing up?**
- Check your config path is correct and absolute
- For Claude Code: `.mcp.json` must be in the workspace root (the folder you open), not inside `mageNT/`
- Actually restart Claude (quit it completely)
- Run `python server.py` to see any errors

**Python not found?**
- Use full path to python in your config
- Or add Python to PATH

**Import errors?**
```bash
cd mageNT
pip install -r requirements.txt
```

## What's Where

```
mageNT/
├── server.py                    # MCP server
├── config.yaml                  # Your settings
├── install.sh / install.bat     # Automated installers
├── agents/                      # The 39 agents (incl. coordination/team_lead)
│   ├── schemas.py               # Pydantic response schemas for prompt outputs (SecurityReport, ADR, ...)
│   └── spec_schemas.py          # Pydantic schemas for the magent_* spec lifecycle (Constitution, FeatureSpec, ...)
├── skills/                      # Reusable skills (scaffold, test, debug, security, etc.)
├── rules/                       # Code quality rules
├── hooks/                       # Automation hooks
├── workflows/                   # Multi-agent workflow templates
├── specs/                       # Spec-driven development output (created at runtime)
├── config/
│   └── dispatch.yaml            # Per-agent install mode (subagent / skill / mcp_only)
├── tools/
│   ├── generate_dispatch.py     # Renders subagent + skill markdown from agent classes
│   ├── dispatch_manifest.py     # SHA-tracked manifest for safe upgrade/uninstall
│   └── validate_spec.py         # `magent validate <spec-id>` — schema + cross-ref checker
├── utils/                       # Orchestration, spec store, skill registry, prompt builders
│   ├── spec_pipeline.py         # Phase 7 orchestration glue (single + multi-agent phases, gates, escalation)
│   └── test_framework_detector.py  # Auto-detect pytest / vitest / jest / go test / cargo test
└── tests/
    ├── test_hooks.py / test_rules.py
    ├── test_spec_schemas.py     # Phase 7A — 29 schema validators
    ├── test_spec_pipeline.py    # Phase 7C — full pipeline e2e with stub LLMs
    └── prompt_eval/             # Multi-model eval harness (run_matrix.py, build_report.py)
```

## Testing

```bash
python -m pytest tests/ -v
```

## Requirements

- Python 3.10+
- Any MCP client (Claude Desktop, Claude Code, Cline, Continue, etc.)

## License

MIT
