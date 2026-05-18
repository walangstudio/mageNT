# Changelog

All notable changes to mageNT are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

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
