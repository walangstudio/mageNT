# Release Team

Go / no-go gate across three angles: quality, deployment, and delivery.
Designed to run minutes before cutting a release branch.

## Prerequisites

- Claude Code v2.1.32+, agent-teams flag enabled
- `magent-{qa_engineer,devops_engineer,delivery_manager}` installed at `~/.claude/agents/`

## Prompt

```
Create an agent team to assess release readiness for <BRANCH OR TAG>.
Spawn three teammates:

- qa (magent-qa_engineer): smallest test set that would prove this release
  is safe. Report: which tests cover the riskiest changes, which gaps remain,
  and whether the suite is green.
- devops (magent-devops_engineer): walk the deploy path. Are the CI pipeline,
  Dockerfile, manifests, and rollback plan all current? Cite the last green
  deploy and what changed since.
- delivery (magent-delivery_manager): independent go / no-go opinion based on
  the punch list. Be willing to say "not yet" and back it with evidence.

Each teammate works independently. When all three are idle, synthesize and
output one of three verdicts: go | go-with-conditions (list the conditions) |
not-yet (list the blockers).
```

## Expected output

Three teammate sections, then a single verdict line. Conditions or blockers
named explicitly with the teammate who raised each.

## Cleanup

```
Ask each teammate to shut down and wait for every teammate's shutdown
confirmation, then clean up the team.
```
