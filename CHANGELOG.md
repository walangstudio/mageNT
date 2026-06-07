# Changelog

All notable changes to mageNT are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.8.0] - 2026-06-05

### Added

- **Objective coding benchmark as a committable gate.**
  `tests/prompt_eval/coding/` now ships 16 tasks (Python + JavaScript) each with
  a **visible** test and a never-shown **held-out** test (anti-gaming), an
  OpenAI-compatible provider runner (NVIDIA NIM, truststore TLS), `--trials`, and
  a `best_of_n` condition. Baseline + after results in `results/`; full write-up
  in [`docs/raw-vs-magent-coding.md`](docs/raw-vs-magent-coding.md).
- **Best-of-N execution selection** in `magent_implement` (opt-in
  `code_best_of_n` in `config/providers.yaml`): sample N candidates at a higher
  temperature on the first attempt, keep the one that passes the failing test.
  Default 1 (single sample), so behaviour is unchanged until enabled. Inert under
  passthrough.
- **Spec-level constraint enforcement** — close the "the test isn't the whole
  spec" gap an e2e run exposed (llama-3.1-8b passed an `eval()`-free FR by
  writing `return eval(expr)`; the visible test only checked results).
  `FunctionalRequirement` gains a typed `constraints` list (`forbid`/`require` a
  code token, optional regex), and a narrow heuristic also mines FR /
  success-criteria prose for the common "no `eval()`" / "without subprocess"
  shape. The implement loop checks the written code against them
  (`utils/constraints.py`): a violated `forbid` (e.g. `eval` used when the FR
  bans it) drives the repair loop and, if it survives, fails the task outcome
  even when the test passes — and is never recorded as a clean pass in the
  trace. Declared constraints are also rendered into the task prompt, so the
  host sees them under passthrough. No constraints declared -> zero behaviour
  change. (`agents/spec_schemas.py`, `utils/implement_runner.py`,
  `tests/test_constraints.py`.)

### Changed

- **Adaptive, model-aware repair loop** (`utils/implement_runner.py`). A live A/B
  showed re-stating a spec constraint each repair round *primes* a strong model
  toward the banned token (qwen3.5 `eval` 0→4/5; the
  [LLMs-cannot-self-correct](https://arxiv.org/abs/2310.01798) effect). Now the
  constraint lives in the initial prompt only; the repair loop re-states it once
  and only for weak models (`weak_models` in `config/providers.yaml`), the gate
  still enforces it on every tier (silent violations stay 0). Plus identical-code
  early-stop and no-blind-re-prompt to cut wasted provider calls
  ([BEACON](https://arxiv.org/html/2510.15945)). Measured: weak-model (llama-8b)
  silent violations 4/6→0/6; strong-model repair-amplification removed
  (final `eval` 4/5→2/5).
- **Prompt-cache breakpoints on the Anthropic provider** (`utils/llm_adapter.py`):
  the static system prompt is sent with `cache_control`, and usage now reports
  cache create/read tokens — ~90% input cost / ~85% latency off the prefix on a
  multi-task run. Dispatchers keep static-prefix/volatile-suffix ordering (pinned
  by a passthrough-ordering test).
- **Anti-over-engineering guardrails on all 26 code agents** (`CodeDisciplineMixin`):
  no top-level demo/`print()` statements, no standard-library-name shadowing
  (the `parse_qs` RecursionError class of bug), no needless class/Enum
  scaffolding, output only the requested symbols. Measured: recovered the
  weak-model persona regression (llama-3.1-8b persona 68%->79%, held-out 25->35)
  and improved the strong model (llama-3.3-70b persona 85%->93%, repair loop to a
  perfect 48/48). No regression on either model.
- **Code-generation temperature is now configurable and low by default**
  (`code_temperature: 0.1` for code/test agents; design agents stay warm).
  Threaded through every dispatcher in `utils/llm_adapter.py`. Lower temperature
  raises pass@1 and removes the nondeterminism seen at the provider default.
  No effect on passthrough.
- **Deeper repair loop**: default budget 2->3, and failure feedback now sends a
  structured excerpt (assertion / exception / tail) instead of a blind
  2500-character truncation.

---

## [0.7.6] - 2026-06-04

### Fixed

- **Teammates again ignored `shutdown_request` (orphaned panes).** A field repro
  on 0.7.5 showed a `magent-hono_developer` teammate waking to a
  `shutdown_request`, emitting a bare `idle_notification`, and never sending
  `shutdown_response` — leaving a pane that only a hard kill closed (a
  general-purpose teammate in the same team acked correctly). The capability and
  the instruction were both already present (`SendMessage` is auto-injected
  regardless of the `tools:` allowlist; the body is *appended to*, not replacing,
  the default teammate prompt), so the defect was **salience**: the
  `TEAM_CONTEXT_BLOCK` opened with a teammate-detection + one-shot/JSON-only
  hedge that handed a freshly-idle specialist an off-ramp, and the binding action
  sat mid-block after a long role prompt. Restructured **action-first**: the
  block now leads with the exact `shutdown_response`/`plan_approval_response`
  directive and demotes the hedge below it, and every rendered teammate prompt is
  now prefixed with a one-line `<team_protocol_priority>` banner so the protocol
  has primacy as well as recency. Reinstall (`generate_dispatch.py --profile
  teams --force`) to pick it up. (`tools/generate_dispatch.py`,
  `tests/test_team_context.py`.)

## [0.7.5] - 2026-05-26

### Fixed

- **Agent-teams protocol gate no longer keyed on a deprecated env var.** The
  `TEAM_CONTEXT_BLOCK` (`tools/generate_dispatch.py`) gated the report/ledger/
  shutdown protocol on `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` and exempted any
  "one-shot subagent" — so GA teammates spawned via `TeamCreate` + the `Agent`
  tool (background, worktree-isolated) read themselves as exempt, committed
  silently, never reported, and never sent `shutdown_response` (orphan
  processes). The gate is now capability-based (you are a teammate if you can
  `SendMessage`/`TaskUpdate`, a lead messaged you, or a shared `TaskList`
  exists) and explicitly covers the GA path. Closes the Wave-7 review's
  highest-severity findings (silent-commit + orphan-process).

### Added

- **Completion-report rule** in the team protocol: on finishing owned work,
  `TaskUpdate` → completed and `SendMessage` a prose report (SHA/files/tests) in
  the same turn, then await shutdown. A commit without a report is not delivered.
- **Three teammate hygiene rules**: cross-scope minimal edits (no compat shims
  to dodge a non-owned file), wire-up ownership (an added API isn't done until
  its call site is wired or handed off), trace-before-code on integration work.
- **`app_store_check` skill** (`/app-store-check`): static-analysis checklist
  for Apple App Store + Google Play submission rejection rules (Info.plist
  purpose strings, `PrivacyInfo.xcprivacy` required-reason APIs, SDK floor;
  Android `targetSdkVersion`, `android:exported`, foreground-service types,
  sensitive permissions, 16 KB native alignment). Affinity-linked to the mobile
  agents.
- **Test-against-spec discipline** added to `sdet`, `qa_engineer`, and
  `automation_qa` heuristics (a test that pins observed buggy output green-lights
  the bug).
- **Persona enrichment**: `cloudflare_expert` + `hono_developer` platform
  pitfalls (sendBeacon Content-Type, falsy-vs-typeof guards, env-var URL
  interpolation, D1 datetime); `ios_developer`/`android_developer`/
  `react_native_developer` store-submission best practices.
- **Parallel dispatch playbook** in `docs/AGENT_TEAMS.md` (worktree baseRef,
  line-range briefing, wire-up ownership, trace-first, mandatory post-dispatch
  code review, selective-Opus).

## [0.7.4] - 2026-05-25

### Added

- **6 new agents** (39 → 45). `code_reviewer` (read-only general PR/diff
  reviewer — correctness/readability/maintainability; joins `magent_audit` as a
  5th reviewer), `refactoring_specialist` (behaviour-preserving structural
  cleanup under green tests), `observability_engineer` (logs/metrics/traces/SLOs),
  `data_engineer` (pipelines/warehousing/data-quality), `ml_engineer`
  (reproducible training/eval/serving/MLOps), `accessibility_specialist`
  (WCAG 2.2 AA). `code_reviewer` is read-only in `TEAMS_TOOLS`; the rest are
  implementers. `ReviewerFinding.reviewer` extended to accept `code_reviewer`.
- **Objective coding eval** (`tests/prompt_eval/coding/`) — scores by *executing
  the hidden test* (pass@1), not a judge. Compares three conditions per task:
  `raw` (plain senior-engineer prompt ≈ raw Claude), `persona` (magent agent
  prompt), `persona_loop` (persona + the verify→repair loop). Provider-pluggable
  (`run(llm_fn, …)`); mechanism unit-tested with a stub (no key needed), live
  numbers need a provider. Closes the gap that the existing prompt eval only
  measured review/advisory tasks, never coding.
- **5 execution-grounded quality skills** (`skills/quality/`) that actually RUN
  the tool and return structured pass/fail + diagnostics (every prior skill was
  text-only): `lint` (ruff/eslint/golangci-lint/clippy), `typecheck`
  (mypy/tsc/go build/cargo check), `format` (black/prettier/gofmt/rustfmt,
  check or apply), `mutation_test` (mutmut/stryker/cargo-mutants — feeds
  `mutation-score-minimum`), `dependency_audit` (pip-audit/npm audit/
  govulncheck/cargo audit). Auto-detect by stack; a missing tool is *skipped*,
  not a failure.

### Changed

- **`magent_implement` now closes the verification loop** (research-backed:
  static-analysis/test feedback is the dominant code-quality lever). Each task
  runs generate → apply → verify → repair: after writing, the failing test runs
  and the rules engine checks the written files; on failure the diagnostics
  (test output + blocking violations) are fed back to the agent for up to
  `repair_budget` (default 2) retries before the outcome is recorded. Was
  one-shot generate-and-move-on.

### Added (WebFetch — carried from prior 0.7.4 work in this cycle)

- Selective `WebFetch`/`WebSearch` for `security_engineer` (CVE / advisory
  lookups), `debugging_expert` (library-bug / upstream-issue lookups during
  RCA), and `cli_installer_developer` (package-registry / version checks).
  Per-agent only — network egress is a prompt-injection vector, so it is never
  blanket-granted. Applied to `TEAMS_TOOLS` (`--profile teams`) and, for the two
  subagent-mode reviewers, to `config/dispatch.yaml`. `cli_installer_developer`
  is `mcp_only`, so it gets the grant under teams mode only.

### Fixed

- Stale `config/dispatch.yaml` header comment referenced a removed
  `TEAMS_READONLY_AGENTS` symbol; corrected to describe the actual `TEAMS_TOOLS`
  classification.

### Changed

- **Code quality + coordination hardening.**
  - Parallel phases (`run_multi_agent_phase`, used by `magent_audit`/`magent_plan`)
    now retry a failed/timed-out contributor once and exclude it instead of
    crashing or merging an `"Error: …"` string as real input. The merger is told
    which reviewers are missing, and `PhaseResult.failed_contributors` records
    them. `magent_audit` forces the persisted Audit off `GO` and appends a
    blocking finding when a reviewer never responded, so `magent_release` blocks
    deterministically on an incomplete audit.
  - `magent_audit` gained an optional `project_root`: when given, `check_code`
    (release profile) runs over the files the implementation trace touched and
    the violations are handed to the reviewers (grounds findings in the rules
    engine instead of pure prose).
  - `magent_implement` now runs tasks in dependency order (topological sort over
    `Task.depends_on`, previously ignored) and errors on a dependency cycle.
  - The `config.yaml` `rules:` block now actually drives the engine (was built
    with defaults and ignored). `rule_settings` is keyed by friendly rule name.
    Added a `release` strictness profile (warnings block) selectable via the new
    `check_code` `profile` argument.

### Added

- `MutationScoreRule` (`mutation-score-minimum`, testing category):
  metadata-driven like `TestCoverageRule`, threshold from
  `config.yaml rule_settings.mutation-score-minimum.min_score` (default 60).
  Makes the mutation-testing bar the QA/SDET prompts preach actually
  representable and enforceable.

### Docs

- `docs/AGENT_TEAMS.md` now documents teammate teardown across all three
  backends (tmux / iTerm2 / in-process). A teammate's shutdown action is
  backend-agnostic — it only sends `shutdown_response`; closing the pane is the
  runtime's job (`shutdown_approved` carries `paneId` + `backendType`, verified
  live as `in-process` on Windows). Flags upstream iTerm2 bug
  claude-code#24385 (pane lingers because `async_close()` is never called) and
  distinguishes it from the idle-miss (teammate still alive). `magent-team_lead`
  gained a matching step so it surfaces a leftover iTerm2 pane as the upstream
  bug instead of re-sending a shutdown_request.

---

## [0.7.3] - 2026-05-24

### Fixed

- Teammates still idled instead of acking protocol messages — not specific to
  any role; every agent shares the same `TEAM_CONTEXT_BLOCK`. Added rule 0
  (PROTOCOL MESSAGES FIRST): at the start of every turn, before new work, a
  `shutdown_request` or `plan_approval_request` is answered first. For shutdown
  it defers to rule 5's sequencing — close the open ledger task
  (`TaskUpdate` -> completed), then send `shutdown_response` — so a teammate
  cannot ack shutdown while leaving a task `in_progress`.
- Generalized the handshake to `plan_approval_request`: rule 5 now gives the
  literal `plan_approval_response` payload (`approve` + `feedback`), matching
  the framework's protocol-response schema.

### Changed

- `magent-team_lead` nudge is now mandatory, not optional: the lead must not
  report a teammate as "parked"/unresponsive until it has sent the literal
  nudge payload and repeated it once; escalate only after two ignored nudges,
  naming the teammate and outstanding `request_id`. Same cycle covers a missed
  `plan_approval_request`.
- `docs/AGENT_TEAMS.md` documents protocol-first handling and the mandatory
  nudge cycle.

### Docs

- README agent counts synced to the current roster: 37 → 39 agents (after
  `hono_developer` + `cloudflare_expert`), and the `subagents` profile count
  11 → 13.

## [0.7.2] - 2026-05-19

### Fixed

- Teams-mode shutdown handshake. Teammates went idle on a `shutdown_request`
  but never terminated, so the lead could not disband the team (cleanup /
  `TeamDelete` fails while any teammate is active). `TEAM_CONTEXT_BLOCK` rule 5
  now (a) explicitly overrides the JSON-only persona's "no open task = done =
  idle" instinct — the arrival of a `shutdown_request` IS the turn's required
  action; (b) gives the literal `shutdown_response` payload to send, echoing
  the verbatim `request_id`; (c) carves the `shutdown_response` out of the
  rule-2 ban on structured-blob messages. Verified by a live agent-teams test:
  with the first (weaker) wording the teammate still idled; the strengthened
  rule + lead nudge produce a correct `shutdown_approved` (request_id echoed)
  and clean `teammate_terminated` + `TeamDelete`.
- `magent-team_lead` now drives the handshake AND its recovery: send each
  teammate a `shutdown_request`; when a teammate idles without a
  `shutdown_response` (expected on first request), immediately send a
  plain-text nudge with the literal payload (the proven-reliable path) rather
  than waiting; only run cleanup once every teammate has emitted an approval.
  New escalation for a teammate that never answers or repeatedly rejects.

### Changed

- `docs/AGENT_TEAMS.md` documents the shutdown handshake ("idle != shut
  down"); the four `examples/teams/*` preset cleanup prompts now ask each
  teammate to confirm shutdown before cleanup.

## [0.7.1] - 2026-05-18

### Changed

- Teams-mode tool grants now driven by an explicit per-agent `TEAMS_TOOLS`
  map (implementer / docs-only / advisory) replacing the binary readonly-set
  heuristic. Developers, `system_architect`, and `delivery_manager` get
  `Edit`/`Write` (write their own code/ADRs/release docs); pure reviewers
  (`security_engineer`, `business_analyst`, `product_manager`,
  `ui_ux_designer`, `team_lead`) stay read-only; `technical_writer` is
  docs-only (no `Bash`); `python_backend` adds `NotebookEdit`.
- Developer agents now declare an explicit `tools:` allowlist in
  `config/dispatch.yaml` instead of relying on an implicit teams-mode default.
- Hardened the `TEAM_CONTEXT_BLOCK` task-ledger protocol: claiming
  (`in_progress`) before work and completing (`completed`) on report is now
  unconditional and gated, not optional — fixes teammates leaving tasks
  `pending`.

### Added

- `staff-implementers` seniority profile (opt-in opus for the developer
  roster).
- Installer auto-promotes `--profile full` → `teams` when run with
  `--enable-teams` and `-c claude`, so the full 39-agent roster is generated.

## [0.7.0] - 2026-05-14

### Added

#### Claude Code agent-teams support (experimental)

Wires mageNT's 36 specialist agents (plus a new `magent-team_lead`
coordinator) into Claude Code's experimental
[agent-teams feature](https://code.claude.com/docs/en/agent-teams) (requires
Claude Code v2.1.32+, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`). Teammates
are spawned by subagent type and inherit the `tools:` allowlist + body —
not `skills` or `mcpServers` — so agent bodies must be self-contained.
mageNT bodies already were.

- `--profile teams` (`tools/generate_dispatch.py`) — emits every registered
  agent class as a subagent regardless of `dispatch.yaml` mode, so every
  team preset has a complete roster (37 agents incl. `magent-team_lead`).
- Each rendered subagent body now ends with a `## Team Context` block
  reminding the teammate that `SendMessage` is always available in a team
  regardless of the frontmatter `tools:` allowlist.
- `agents/coordination/team_lead.py` — new Principal-level coordinator
  (`magent-team_lead`) that routes requests to the right specialist roster,
  forwards findings between teammates via `SendMessage`, and synthesizes
  outputs.
- `examples/teams/` — four copy-pasteable team prompts:
  `audit-team`, `spec-team`, `release-team`, `stack-build-team`.
- `hooks/teams/task_completed_validate.py` — `TaskCompleted` hook that runs
  `magent validate` against `specs/`; exit 2 rejects the completion and
  surfaces validator errors to the teammate.
- `hooks/teams/teammate_idle_summary.py` — `TeammateIdle` hook that appends
  one-line status to `specs/active/team_log.md` for the lead's synthesis.
- `tools/enable_teams.py` — idempotent JSON merge that sets
  `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `~/.claude/settings.json`.
- `install.sh` / `install.bat`: `--enable-teams` / `--no-enable-teams`
  flags and interactive prompt when installing in `subagents` or `hybrid`
  mode.
- `magent doctor` (CLI) — reports agent count, env flag, Claude Code
  version (must be ≥ 2.1.32), and per-preset roster completeness.
- `docs/AGENT_TEAMS.md` — full guide: prereqs, install, presets, hooks,
  caveats.

#### Seniority resolver

Six-layer override (CLI → project → user → profile → class default →
fallback) for per-agent `expertise_level`. Resolved at install time and
baked into the rendered subagent markdown — no runtime lookup.

- `tools/resolve_seniority.py` — `resolve(agent_name, class_default)`.
- `config/seniority_profiles.yaml` — `default`, `principal-heavy`,
  `flat-senior` presets.
- `magent generate --seniority <a>=<level>,...` and
  `--seniority-profile <name>` flags.
- Per-machine override at `~/.magent/seniority.yaml`; per-repo at
  `./magent.seniority.yaml`.

Baked class-level defaults:
- **Principal**: `system_architect`, `cloud_architect`, `delivery_manager`,
  `product_manager`, `team_lead`.
- **Staff**: `security_engineer`, `performance_engineer`, `sdet`,
  `devops_engineer`, `database_administrator`.
- **Senior**: every developer + `qa_engineer`, `automation_qa`,
  `debugging_expert` (class default — no per-agent override needed).
- **No level word** (`""`): `business_analyst`, `technical_writer`,
  `ui_ux_designer`, `integration_specialist`.

#### Team-model selection

`BaseAgent.team_model` maps `expertise_level` → Claude model alias
(Principal/Staff → `opus`, Senior/specialist → `sonnet`). Emitted into the
frontmatter `model:` field by `generate_dispatch` and read by Claude Code
when spawning the teammate. Inert outside agent-teams context.

### Changed

#### Role-line renderer fix

Generated subagent bodies opened with `"You are a Principal <Role>, <Role>
specializing in <X>."` because (a) `_instantiate_agent` hardcoded
`expertise_level="principal"` and (b) the class docstring's first line was
injected as `specialization` and concatenated with the role. Both removed:

- `_instantiate_agent` now respects each class's `expertise_level` (with
  resolver overrides) and no longer touches docstrings.
- `PromptBuilder.build_agent_prompt` drops the `specialization` segment
  when it restates the role; emits `"You are a <Role>."` with no level
  word when `expertise_level` is empty (specialist roles).

Re-running `magent generate` overwrites the stale installs. Test:
`tests/test_prompt_builder.py` (5 cases).

### Notes

- Behavior change for users who regenerate: subagent role lines now reflect
  the four-tier seniority table, not the previous uniform "Principal".
- No API break. `BaseAgent`'s public surface, MCP tool list, and skill list
  are unchanged.

---

## [0.4.0] - 2026-03-20

### Added

#### Spec-Driven Development (SDD)

Five new MCP tools that implement a structured spec → architecture → parallel build → audit cycle:

- `create_spec` — Business Analyst generates a requirements spec from project name, description, and a list of raw requirements. Stores to `specs/{spec_id}/spec.md` with YAML front-matter. Returns a spec ID used by all subsequent tools.
- `create_arch_spec` — System Architect generates a full architecture spec (tech stack, component design, API contracts, data models) from a requirements spec. Stores to `specs/{spec_id}/arch_spec.md`.
- `run_parallel_agents` — Runs multiple domain agents concurrently via `asyncio.gather`. Auto-selects agents from the arch spec using keyword scanning when no explicit list is given. Default phases: `build` (implementation agents) and `qa` (QA + Security). Results auto-saved to `specs/{spec_id}/phase_{phase}_results.json`.
- `audit_spec` — Delivery Manager audits all phase results against the original acceptance checklist. Auto-loads saved phase results — no manual data passing required. Returns per-requirement `MET`/`PARTIAL`/`MISSING` status and a go/no-go decision.
- `list_specs` — Lists all specs in the store with metadata.

New supporting modules:
- `utils/spec_store.py` — file I/O for spec lifecycle with path-traversal protection
- `utils/spec_builder.py` — pure prompt/context builders; context (reference material) and task (instruction) are kept separate to avoid prompt degradation
- `utils/skill_registry.py` — skill instantiation, agent→skill affinities, and keyword-based skill auto-selection
- `utils/parallel_orchestrator.py` — async orchestrator with per-agent timeout (90s) and word-boundary keyword matching

#### Skill MCP Tools

10 skills now exposed directly as `skill_*` MCP tools callable from any client:

- `skill_debug_code` — structured debugging guidance
- `skill_analyze_error` — error/exception analysis
- `skill_scaffold_react` — React + Vite project scaffold
- `skill_scaffold_nextjs` — Next.js App Router scaffold
- `skill_scaffold_fastapi` — FastAPI + Pydantic scaffold
- `skill_scaffold_express` — Express.js scaffold
- `skill_security_scan` — OWASP-aligned security checklist
- `skill_generate_tests` — test generation guidance
- `skill_run_tests` — test runner guidance
- `skill_check_versions` — dependency version and compatibility check

Skills are also auto-invoked during `run_parallel_agents` based on the arch spec content and each agent's affinity set.

#### Workflows

- `tdd` — 9-step Test-Driven Development workflow following the red-green-refactor cycle: acceptance criteria → testable architecture → failing tests (red) → minimum implementation (green) → refactor → E2E suite → security review → documentation → delivery sign-off

#### TDD Prompt

- `start_workflow` — when starting any non-TDD workflow, appends an optional suggestion to use the `tdd` workflow instead
- `create_spec` — after spec creation, surfaces the `tdd` workflow as an alternative to the standard `create_arch_spec` flow

### Changed

#### Agent Enhancements

- `base.py` — added `dispatch_to_llm_async` for non-blocking parallel LLM dispatch; uses `get_running_loop()` (replaces deprecated `get_event_loop()`)

#### New Agents (1)

- `sdet` — Software Development Engineer in Test. Focuses on test architecture, testability engineering, test infrastructure (Testcontainers, factories, harnesses), toolchain ownership (coverage enforcement, mutation testing, property-based testing), and CI quality gates. Distinct from `qa_engineer` (strategy/manual) and `automation_qa` (E2E framework execution).

#### Prompt Quality

- `utils/prompt_builder.py` — `expertise_level` now rendered with `.capitalize()` so config value `"principal"` displays as `"Principal"` in all system prompts
- `utils/spec_builder.py` — context builders (reference material passed as LLM context) and task builders (instructions only) are strictly separated; no role re-statement in task strings; arch spec content never duplicated between task and context

---

## [0.3.0] - 2026-02-24

### Added

#### Installer

- `install.bat` — new Windows CMD/PowerShell installer with full feature parity with `install.sh`
- `--global` flag — writes Claude Code MCP config to `~/.claude/mcp.json` (global user config) instead of the workspace-local `.mcp.json`; valid with `-c code` or `-c both`
- `--update -c <client>` — reconfigures MCP client paths after upgrading; previously `--update` ignored `-c`

### Changed

#### Installer

- `install.sh` / `install.bat` — idempotent re-runs: re-running at the same version exits cleanly with "Already at vX.X.X. Nothing to do." instead of prompting to overwrite
- `install.sh` / `install.bat` — removed interactive "Overwrite? [y/N]" prompt from MCP config step; replaced with silent idempotency check (skips if python path unchanged, updates silently if changed, `--force` bypasses)
- `install.sh` / `install.bat` — `--update` now shows version diff (`Upgrading vX → vY`) and exits early when already at current version
- `install.sh` — Claude Code config now written to parent workspace directory (e.g. `../` relative to mageNT) instead of inside the mageNT folder; the old location only worked when Claude Code was opened from the mageNT directory itself
- Fixed uninstall crash under `set -euo pipefail` when `.venv` was absent (`get_venv_python` now uses `|| true` guard)

---

## [0.2.0] - 2026-02-23

### Added

#### New Agents (13)

**Development — Frontend**
- `svelte_developer` — Svelte, SvelteKit, Sapper, TypeScript, Vite

**Development — Backend**
- `integration_specialist` — REST/GraphQL APIs, Webhooks, Message Queues, ETL, Third-party SDKs
- `rust_backend` — Rust, Tokio, Axum, Actix-web, Cargo, WebAssembly

**Development — Mobile (4 specialists replacing the generic agent)**
- `flutter_developer` — Flutter, Dart, Riverpod, Bloc, platform channels
- `react_native_developer` — React Native, Expo, EAS Build/Update, Detox, Maestro
- `android_developer` — Kotlin, Java, Jetpack Compose, MVVM, Hilt, Coroutines
- `ios_developer` — Swift, Objective-C, SwiftUI, UIKit, async/await, XCUITest

**Business**
- `delivery_manager` — SDLC completion audits, go/no-go readiness reports, Definition of Done

#### New Workflows (4)

- `new_system` — Full 15-step greenfield project lifecycle (requirements → design → dev → test → docs → deployment → sign-off)
- `add_feature` — 10-step feature addition with impact analysis, QA, and delivery sign-off
- `bug_fix` — 7-step diagnose → fix → regression → sign-off workflow
- `full_audit` — 9-step comprehensive health check across architecture, security, performance, QA, CI/CD, and docs

#### Installer

- Added `--update` flag to `install.sh` — upgrades dependencies and merges new agent/workflow blocks into existing `config.yaml` without overwriting user customizations

### Changed

#### Agent Enhancements

- `java_backend` — added Spring WebFlux, Spring AMQP/Kafka responsibilities; Spring Boot DevTools, Actuator, and profiles best practices; updated specialization to include Spring Framework and Gradle
- `go_backend` — added Tauri desktop app responsibilities and best practices; updated specialization to include Tauri
- `qa_engineer` — significantly expanded to cover manual testing (exploratory, regression, test case authoring), test management tools (TestRail, Xray, Zephyr), BDD (Cucumber, pytest-bdd), API testing (Postman, REST Assured), and explicit tool coverage (Jest, Pytest, JUnit, NUnit, Mocha)
- `automation_qa` — expanded to cover full E2E toolchain (Playwright, Cypress, Selenium, WebdriverIO, TestCafe, Puppeteer), mobile automation (Appium, Detox, Maestro, XCUITest, Espresso), API automation (Newman, REST Assured, Karate, SoapUI), performance testing (k6, Gatling, Locust, Artillery), visual regression (Percy, Chromatic, Applitools), contract testing (Pact, Spring Cloud Contract), BDD (Cucumber, SpecFlow, Behave), and reporting (Allure, ReportPortal)

#### Workflow Improvements

- `full_stack_web` — added UI/UX Designer, Security Engineer, Automation QA, Technical Writer, Delivery Manager steps
- `mobile_app` — added Security Engineer, Automation QA, Technical Writer, Delivery Manager steps
- `saas_platform` — added Product Manager, UI/UX Designer, QA Engineer, Automation QA, Technical Writer, Delivery Manager steps
- `multi_tenant_app` — added QA Engineer, DevOps Engineer, Delivery Manager steps
- `legacy_migration` — added Security Engineer, Technical Writer, Delivery Manager steps

#### Documentation

- `config.example.yaml` — updated to include all new agents and workflows; updated stale specializations
- `README.md` — updated agent count (24 → 32), expanded team table, updated workflow list

---

## [0.1.0] - Initial Release

- 24 specialist agents across business, development, data, infrastructure, and quality domains
- 19 workflow templates
- Rules engine with security, style, testing, git, and performance categories
- Automation hooks (pre-commit, pre-edit, post-edit, session lifecycle)
- Cross-platform installer (`install.sh`) supporting Claude Desktop and Claude Code
