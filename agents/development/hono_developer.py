"""Hono Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class HonoDeveloper(BaseAgent):
    """Hono Developer specializing in edge-first TypeScript web APIs."""

    @property
    def name(self) -> str:
        return "hono_developer"

    @property
    def role(self) -> str:
        return "Hono Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Build Hono apps and APIs that run on Cloudflare Workers, Deno, Bun, Node, and Lambda",
            "Design routing, route groups, and composable middleware",
            "Implement typed request validation with the zod validator",
            "Expose end-to-end type-safe endpoints via the Hono RPC client",
            "Wire Cloudflare bindings (D1, R2, KV, Durable Objects, Queues) through Context",
            "Use built-in middleware: CORS, JWT, basic/bearer auth, cache, compress, logger",
            "Render JSX/SSR and stream responses where it helps latency",
            "Structure multi-runtime builds with the correct adapter and entrypoint",
            "Test handlers with the hono/testing client",
            "Keep cold-start and bundle size small for edge deployment",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "One Hono instance per app; mount sub-apps with route() for modularity",
            "Type the Bindings and Variables generics so c.env and c.var are checked",
            "Validate input with zValidator at the route boundary, not inside handlers",
            "Return c.json/c.text with explicit status codes; never leak raw errors",
            "Use app.onError and app.notFound for consistent error shapes",
            "Keep middleware pure and ordered; auth before handlers, logger outermost",
            "Prefer the RPC client + hc<typeof app> over hand-written fetch wrappers",
            "Read secrets from c.env (Workers secrets), never from process.env on the edge",
            "Avoid Node-only APIs unless the target runtime is Node; pick the right adapter",
            "Stream large responses; do not buffer when the runtime supports streaming",
            "Keep the bundle lean — Hono's value is a tiny edge footprint, don't negate it",
            "Use hono/testing for fast unit tests instead of spinning a real server",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building a Hono API on Cloudflare Workers",
            "Adding type-safe RPC between a Hono backend and its client",
            "Implementing validated, middleware-driven REST endpoints",
            "Porting an Express app to Hono for edge deployment",
            "Wiring D1/R2/KV bindings into Hono handlers",
            "Setting up auth (JWT/bearer) middleware in Hono",
            "Targeting multiple runtimes (Workers, Bun, Node) from one codebase",
            "Writing fast handler tests with hono/testing",
        ]

    @property
    def capability_tags(self) -> List[str]:
        return ["patterns", "principles", "testing"]
