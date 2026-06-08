# Raw vs magent — coding pass@1

Within-model A/B. Same model under every condition, so the only variable is
magent's contribution (persona prompt, repair loop, best-of-N). Objective
scoring: the model emits a solution file, a hidden test decides pass/fail.
Harness: `tests/prompt_eval/coding/run_coding_eval.py`, 16 tasks
(`coding_tasks.yaml`, Python + JavaScript), 3 trials per cell.

## Conditions

- **raw** — a plain "you are a senior software engineer" prompt (≈ raw model).
- **persona** — the magent agent's `get_system_prompt()`, one shot.
- **persona_loop** — persona + the verify→repair loop (re-prompt with the test
  failure, up to 3 retries).
- **best_of_n** — persona, 4 candidates at temperature 0.4, keep the first that
  passes the test (execution selection).

Two tests per task: a **visible** test (the repair loop sees its failure output)
and a **held-out** test (extra edge cases, never shown) that scores whether the
final code actually generalises. Held-out is the honest quality signal; visible
pass-rate saturates.

## The defect this work fixed

On a weak model the magent **persona made code worse than raw**. Captured 8b
failures: `parse_qs` written as `from urllib.parse import parse_qs` + a
self-named wrapper (RecursionError) with top-level demo `print()`s; `roman_to_int`
wrapped in a needless `Enum`. The verbose senior-*specialist* persona pushed a
small model toward over-engineering and contract violations that a terse prompt
avoided. Root cause: coding agents defined no anti-patterns, and code was
generated at the provider default temperature (~1.0).

## Changes measured

- **Anti-over-engineering guardrails** (`CodeDisciplineMixin`) on all 26 code
  agents: no top-level demos/prints, no stdlib-name shadowing, no needless
  scaffolding, output only the requested symbols.
- **Low code-gen temperature** (`code_temperature: 0.1`) — the harness already
  holds temperature at 0, so the tables below isolate the prompt change; the
  config change carries the same effect into production providers.
- **Deeper repair loop** (budget 2→3) with structured failure excerpts.
- **Best-of-N** execution selection (opt-in, `code_best_of_n`).

## Results — llama-3.1-8b (weak), 3 trials, 48 cells/condition

| Condition | visible before → after | held-out before → after |
|---|---|---|
| raw (control) | 87% → 89% | 33 → 33 |
| persona | **68% → 79%** | **25 → 35** |
| persona_loop | 85% → 89% | 34 → **39** |
| best_of_n | 87% → 91% | 36 → 38 |

raw moved +1 cell (NIM is nondeterministic even at temp 0), so persona's
+10pp visible / +10 held-out is signal above noise. The over-engineering victims
recovered under persona: balanced 0/3→3/3, roman 1/3→3/3, validate_ipv4 0/3→3/3.

## Results — llama-3.3-70b (strong), 3 trials — no-regression gate

| Condition | visible before → after | held-out before → after |
|---|---|---|
| raw (control) | 100% → 97% | 42 → 41 |
| persona | 85% → **93%** | 37 → 42 |
| persona_loop | 89% → **100%** | 40 → 44 |
| best_of_n | 97% → 97% | 44 → 44 |

The strong model improved (persona +8pp, loop to a perfect 48/48) or held flat.
The raw 100→97 is one nondeterministic cell, not a real move.

## Takeaways

1. **magent's coding value is the loop + best-of-N, not the persona text.** On a
   capable model both magent conditions beat raw on held-out robustness
   (persona_loop 39/48 and best_of_n 38/48 vs raw 33/48 on 8b; perfect/near
   on 70b). The code passes more *unseen* edge cases.
2. **The persona prompt was net-negative on weak models until the guardrails.**
   Anti-patterns recovered it (8b persona 68→79%) and improved the strong model
   (70b 85→93%). Carefully qualified ("trivial", "needless") so they never strip
   legitimate structure (LRUCache stayed 3/3 throughout).
3. **Temperature matters.** Code generated at the provider default is
   nondeterministic; `code_temperature: 0.1` is a free pass@1 lever for the
   provider path.

## Cross-model: the Claude family saturates

Tested with real Haiku 4.5 and Opus (via host model overrides, the passthrough
mechanism) on 7 tasks up to competition-hard (regex `.`/`*` matcher, calculator
with unary minus, edit distance, longest-valid-parentheses), scored visible +
held-out:

| | Haiku-raw | Haiku + magent | Opus-raw |
|---|---|---|---|
| all 7 tasks | pass | pass | pass |

Haiku already equals Opus-raw, so magent has nothing to recover. The scaffolding
helps where the base model *fails* — that regime exists for Llama-8b-class models,
not for current Claude models on single-function coding. Don't expect a coding
pass-rate gain from magent on the Claude family; its value there is structural.

## Production end-to-end

The benchmark scores generation quality, not the `magent_implement` MCP pipeline.
That pipeline was verified separately end-to-end against a live provider: a real
`run_implementation` run (NIM Llama-70b, roman numerals) produced a passing file
and a git commit on the first candidate; a harder run (NIM Llama-8b, expression
evaluator) exercised the full machinery — 3 best-of-N candidates plus 2 repair
rounds — before committing. The 8b run originally passed by using `eval()`, which
the visible test did not forbid — a constraint absent from the test was not
enforced. That gap is now closed: a spec can declare the constraint
(`FunctionalRequirement.constraints`, or just write "no `eval()`" in the FR), and
the implement loop checks the written code, drives the repair loop on a
violation, and fails the task if it survives. See
[constraint enforcement](#spec-level-constraints).

## Spec-level constraints

A failing test pins *behaviour*, not forbidden *means* — "evaluate the expression"
is satisfied by `return eval(expr)` as far as the test can tell. A spec can now
declare hard code-level constraints that the implement loop enforces beyond the
test:

- **Explicit:** `FunctionalRequirement.constraints` — a typed list of
  `{kind: forbid|require, pattern, message, regex}`. `forbid eval`,
  `require "async def"`, `forbid os.system`. Durable and unambiguous; prefer this.
- **Heuristic:** a narrow scan of FR / success-criteria prose for the common
  "no `eval()`" / "without subprocess" shape. Conservative by design (only
  `token()` forms and a small dangerous-builtin allowlist) so it almost never
  invents a constraint that wasn't meant. For anything beyond the obvious, write
  an explicit constraint.

Matching is word-boundaried (`forbid eval` flags `eval(` but not `ast.literal_eval`
or `evaluate`) and ignores banned tokens that appear only in comments. A violated
`forbid` drives the repair loop with a "the test won't catch this" message; if it
survives the repair budget, the task outcome is a failure (not a clean pass) even
though the test passed, and the trace never records it as passed. Declared
constraints are also rendered into the task prompt, so the implementer — a
provider model, or the host under passthrough — is told the banned/required tokens
up front. No constraints declared means zero behaviour change.

## Constraint enforcement is tier-aware (measured)

A live A/B (NVIDIA NIM, `forbid eval` on an arithmetic-evaluator task, scored on
whether the final code uses `eval`) shows constraint enforcement helps weak
models and must be applied carefully to strong ones.

**Weak model (llama-3.1-8b), N=6 — the feature's value:**

| | no constraint | with constraint |
|---|---|---|
| attempt-0 used eval | 5/6 | **0/6** |
| **silent violation** (test green, eval used, no error) | **4/6** | **0/6** |

Telling an 8b "no `eval`" works — it stops reaching for `eval` first-try (5/6→0/6),
and the gate catches the rest, so silent violations go to zero.

**Strong model (qwen3.5-122b), N=5 — saturated, and primed by the instruction:**

| | no constraint | constraint (naive repair) | constraint (adaptive) |
|---|---|---|---|
| final used eval | 0/5 | 4/5 | **2/5** |
| clean pass | 5/5 | 1/5 | 2/5 |
| silent violation | 0/5 | 0/5 | 0/5 |

qwen never games `eval` unprompted (0/5). Naively, the repair loop *re-stated*
"no `eval`" every round and drove `eval` **up to 4/5** — the
[LLMs-cannot-self-correct](https://arxiv.org/abs/2310.01798) effect: re-stating
the instruction primes the banned token. The **adaptive** loop (constraint kept
in the initial prompt, never repeated in repair; identical-code early-stop)
removes that amplification (final `eval` ≈ attempt-0). A residual ~2/5 comes from
the *initial-prompt* injection itself priming a saturated model — which is why the
repair nudge is **weak-model-only** and the initial injection is a candidate to
gate by tier too.

The rule, then: **enforce** on every tier (the gate keeps silent violations at 0
everywhere); the **repair nudge** is weak-model-only (shipped); the **initial
injection** still runs on all tiers today, with weak-gating it an open option
(strong models rarely violate an obvious constraint, and the injection itself
mildly primes them). Tier is configured via `weak_models` in
`config/providers.yaml`.

## Repair-loop economy

Two changes cut wasted provider calls without losing pass-rate:

- **Identical-code early-stop** — a repair round that reproduces the previous
  attempt's code carries no new signal, so the loop stops instead of burning the
  rest of the budget ([BEACON](https://arxiv.org/html/2510.15945): adaptive
  stopping matches fixed budgets at 15-35% fewer generations).
- **No blind re-prompt** — when there is nothing new to tell the model (e.g. a
  strong model whose test passed but a constraint survived), the loop stops and
  the gate fails it honestly rather than re-prompting (which only primes).

## Prompt caching (anthropic provider)

The system prompt (persona + anti-patterns + schema) is static across the many
per-task calls in a run, so `_dispatch_anthropic` now marks it as a
`cache_control` breakpoint — [up to ~90% input cost / ~85% latency](https://www.anthropic.com/news/prompt-caching)
off the prefix, no-op below the model's cache minimum. The dispatchers keep the
static prompt as a stable prefix and volatile content (task, constraints) as the
suffix; a test pins the passthrough ordering so the host can cache the persona
too.

## Caveats

- NIM is nondeterministic even at temperature 0; always ≥3 trials, report
  pass-rate not single runs. n=3 means single-cell moves are noise.
- Two languages, `python_backend` / `nodejs_backend` agents, 16 tasks.
- **Passthrough** (the host Claude completes magent's prompt) only sees the
  persona change — temperature, repair loop, and best-of-N fire only when magent
  drives a real provider (Ollama / LM Studio / NIM). The persona improvement was
  separately verified correct on the host-Claude path.

Raw result JSON: `tests/prompt_eval/coding/results/`.
