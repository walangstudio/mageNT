# Audit Team

Parallel review of a PR or branch across four angles: delivery readiness,
security, performance, and quality.

## Prerequisites

- Claude Code v2.1.32+
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `~/.claude/settings.json`
- `~/.claude/agents/magent-{delivery_manager,security_engineer,performance_engineer,qa_engineer}.md` installed
  (run `magent install --profile teams` or `python tools/generate_dispatch.py --profile teams --target ~/.claude`)

## Prompt (paste verbatim to a fresh Claude Code session)

```
Create an agent team to audit the current branch (or PR #<NUMBER>). Spawn four reviewers:

- delivery-manager (use the magent-delivery_manager subagent): identify what's
  missing for release readiness. Output a punch list of done vs. missing.
- security (use the magent-security_engineer subagent): walk the diff for
  OWASP Top 10 and language foot-guns. Output structured findings.
- performance (use the magent-performance_engineer subagent): flag any change
  with measurable runtime, query, or memory impact. Cite the metric.
- qa (use the magent-qa_engineer subagent): find behaviour the test suite no
  longer pins down. Name the missing test and the regression it would catch.

Each reviewer works the diff independently. When all four are idle, synthesize:
group findings by severity, attribute each to its reviewer, and surface
conflicts explicitly. End with a single go / not-yet recommendation.
```

## Expected output

A four-section synthesis grouped by severity, with `[reviewer-name]` attribution
on every bullet. A `Conflicts` section if any reviewers disagree. A final one-line
recommendation: `go` or `not-yet (reason)`.

## Cleanup

```
Clean up the team
```
