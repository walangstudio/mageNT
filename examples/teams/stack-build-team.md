# Stack-Build Team

Greenfield application scoping — picks the stack, sketches the schema, and
drafts the API/UI shape in parallel.

## Prerequisites

- Claude Code v2.1.32+, agent-teams flag enabled
- `magent-{system_architect,react_developer,nodejs_backend,database_administrator}`
  installed at `~/.claude/agents/`

## Prompt

```
Create an agent team to scope a greenfield application: <ONE-PARAGRAPH
PRODUCT DESCRIPTION>. Spawn four teammates:

- architect (magent-system_architect): pick the smallest stack that fits.
  Name the decisions (storage, auth, hosting, queue if any) as ADRs.
- frontend (magent-react_developer): sketch the page graph and component
  tree. No code — just the surface and the data each page needs.
- backend (magent-nodejs_backend): draft the API surface. List endpoints
  with method, path, request/response shape. No code.
- database (magent-database_administrator): draft the schema. Tables,
  columns, indexes, foreign keys. Cite which queries each index supports.

Work in parallel. When all four are idle, synthesize into a single scoping
doc: Architecture (ADRs) | Frontend (page graph) | Backend (API table) |
Database (schema diagram). Flag any cross-team contradictions explicitly —
e.g., a query the schema can't serve, a page with no API behind it.
```

## Expected output

Four labelled sections plus a `Cross-cuts` section that lists every place
two teammates disagreed or one teammate's output didn't fit another's. No
implementation code.

## Cleanup

```
Ask each teammate to shut down and wait for every teammate's shutdown
confirmation, then clean up the team.
```
