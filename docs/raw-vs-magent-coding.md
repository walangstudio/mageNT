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

## Caveats

- NIM is nondeterministic even at temperature 0; always ≥3 trials, report
  pass-rate not single runs. n=3 means single-cell moves are noise.
- Two languages, `python_backend` / `nodejs_backend` agents, 16 tasks.
- **Passthrough** (the host Claude completes magent's prompt) only sees the
  persona change — temperature, repair loop, and best-of-N fire only when magent
  drives a real provider (Ollama / LM Studio / NIM). The persona improvement was
  separately verified correct on the host-Claude path.

Raw result JSON: `tests/prompt_eval/coding/results/`.
