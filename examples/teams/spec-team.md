# Spec / Feature Team

Turns a fuzzy feature request into a FeatureSpec → ImplementationPlan → TaskList
in one parallel pass.

## Prerequisites

- Claude Code v2.1.32+, agent-teams flag enabled
- `magent-{business_analyst,system_architect,product_manager}` installed at `~/.claude/agents/`

## Prompt

```
Create an agent team to scope a new feature: <ONE-PARAGRAPH DESCRIPTION>.
Spawn three teammates:

- requirements (magent-business_analyst): produce a FeatureSpec with FR-### IDs
  (RFC 2119 verbs) and Given/When/Then scenarios. Mark unresolved questions as
  [NEEDS CLARIFICATION].
- architecture (magent-system_architect): produce an ImplementationPlan naming
  the smallest set of high-leverage decisions, the affected modules, and any
  ADRs we'd need to write. No code.
- product (magent-product_manager): produce a priority cut — which FRs are P0
  vs P1 vs cut-this-release. Cite the user value behind each P0.

Work in parallel against the description above. When all three are idle,
synthesize into a single doc: FeatureSpec | Plan | Priorities, with conflicts
between teammates surfaced explicitly. Do not resolve [NEEDS CLARIFICATION] —
list them for the user.
```

## Expected output

Three labelled sections (spec, plan, priorities) with cross-references. An open
questions list pulled from `[NEEDS CLARIFICATION]` markers. No code.

## Cleanup

```
Ask each teammate to shut down and wait for every teammate's shutdown
confirmation, then clean up the team.
```
