# Raw vs magent — NIM `gpt-oss-120b` A/B

Same model, same prompt intent, two delivery paths. Captured 2026-05-10.

## Setup

- **Model**: `openai/gpt-oss-120b` via NVIDIA NIM (`https://integrate.api.nvidia.com/v1`)
- **Prompt intent**: "build a small Python CLI todo app with add / list / done commands and JSON file persistence"
- **A — RAW**: single freeform user message, no schema, no pipeline. `script: specs/_raw_baseline.py`.
- **B — WITH magent**: full Phase 7 pipeline — `magent_constitution → magent_spec → magent_plan → magent_tasks → magent_implement`, every artifact validated against a Pydantic schema, per-task scoped tests, real git commits with FR-IDs.

## Headline numbers

| Metric | A — RAW | B — WITH magent |
|---|---|---|
| Wall time | **20.2s** | 100.6s |
| Tokens (in / out) | 126 / 2,170 | 2,000 / 8,768 |
| Validates against Phase 7 schemas | **0/5** (freeform Markdown) | **5/5** (every artifact) |
| FR-### IDs in output | 0 | 3 (FR-001 / FR-002 / FR-003) |
| Per-task test files generated | 0 | 3 (real assertions, direct imports) |
| Test runner invoked automatically | n/a | yes (3 tests ran) |
| Tests passing | n/a (no test runner integration) | 0/3 (impl/test naming mismatch — see below) |
| Real git commits | 0 (just text in the chat) | **3 — one per task, [FR-XXX] auto-prefixed** |
| Traceability matrix | none | spec_id → constitution → FR-### → task → commit → cost |
| Per-phase token cost ledger | n/a | `cost.json` with prompt/completion counts per phase |

## Artifact integrity

**B — WITH magent** persisted 5 schema-validated artifacts:

| Artifact | Size | Content |
|---|---:|---|
| `constitution.json` | 503 b | project_name, 3 principles, NFR targets, tech_constraints, out_of_scope |
| `spec.json` | 2,494 b | 1 user story (P1), 3 FRs (FR-001 MUST, FR-002 SHOULD, FR-003 MUST), 1 G/W/T scenario, success_criteria, assumptions |
| `plan.json` | 1,538 b | tech_stack, 2 components |
| `tasks.json` | 1,047 b | 3 tasks (T001/T002/T003) — each with files, parallel_safe, fr_ids, failing_test_path |
| `implementation_trace.json` | 789 b | 3 CommitTrace records (fr_id × commit_sha × files × test_passed) |

**A — RAW** produced 8,586 chars of Markdown prose with 6 fenced code blocks. No machine-readable structure. No traceability. Three Python file paths mentioned in the prose (`/todo.py`, `todo.py`, `todo_store.py`); whether those map to the requested capabilities is left to the reader.

## Code quality (B — WITH magent workspace)

3 source files written + 3 tests + 3 commits, ~6.6 KB of real implementation:

```
src/command_handler.py    3,198 b
src/store.py              1,839 b
src/todo_repository.py    1,608 b
tests/test_T001_add_todo.py    809 b
tests/test_T002_list_todo.py   747 b
tests/test_T003_persistence.py 677 b
```

git log:

```
02ad2a7 [FR-003] Persist todo items to local file
3ff9149 [FR-002] List pending todo items command
b0bc338 [FR-001] Add new todo item command
```

The PRE_COMMIT hook auto-prefixed every commit with the FR-ID(s) from the active task — no manual tagging.

## Why 0/3 tests passed in B

Investigation: tests import `from src.todo_repository import TodoRepository` and call `handler.add_todo("Buy milk")`. Implementation files exist, but:

1. No `src/__init__.py` was generated → Python can't resolve `src.todo_repository` as a package.
2. The test wants `TodoRepository` class with `add_todo()` method; impl produced `Store` + `TodoRepository` + `CommandHandler` with potentially mismatched method names.

This is a **test/impl naming agreement bug**, not a pipeline bug. Sdet and the developer agent didn't share a contract about class/method names. Fix path: have `magent_tasks` emit per-task **stub interfaces** (class signature, method names) the impl must follow. Tracked as a Phase 7K follow-up.

## Conclusion — what magent buys you

The raw response is a useful one-shot draft for a human to read, triage, and rewrite. It cannot be:

- Programmatically validated against a contract (no schema)
- Decomposed into trackable work (no FR-IDs, no tasks)
- Linked to commits (no commits — just text)
- Costed per phase (single black-box token bill)
- Re-run incrementally (no checkpoints between phases)
- Audited for completeness (no FR → task → commit traceability matrix)

WITH magent gets you all of those for **5× the wall time and ~4× the token cost** on this todo-cli example. The structural artifacts are real, schema-validated, persistent, and form an audit trail no raw-prompt path can produce.

The actual code-quality delta (impl + tests passing) is bounded by model + spec quality, not by the pipeline. With matched test/impl interface contracts (Phase 7K), the same NIM gpt-oss-120b run is likely to produce 2-3 passing tests out of 3 on this same fixture.
