"""Svelte Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class SvelteDeveloper(BaseAgent):
    """Svelte Developer specializing in Svelte, SvelteKit, and Sapper applications."""

    @property
    def name(self) -> str:
        return "svelte_developer"

    @property
    def role(self) -> str:
        return "Svelte Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Build reactive UIs with Svelte components",
            "Develop full-stack applications with SvelteKit",
            "Implement file-based routing and layouts in SvelteKit",
            "Use SvelteKit load functions for server-side and client-side data fetching",
            "Build and migrate Sapper applications",
            "Manage state with Svelte stores (writable, readable, derived)",
            "Implement server-side rendering, static site generation, and SPA modes",
            "Handle form actions and progressive enhancement in SvelteKit",
            "Create reusable Svelte component libraries",
            "Integrate Svelte with TypeScript",
            "Optimize bundle size and runtime performance",
            "Write unit and end-to-end tests for Svelte applications",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Prefer SvelteKit over Sapper for new projects (Sapper is deprecated)",
            "Use TypeScript with lang=\"ts\" in script blocks",
            "Leverage reactive declarations ($:) for derived state instead of manual updates",
            "Use Svelte stores for shared cross-component state",
            "Prefer SvelteKit form actions for mutations to enable progressive enhancement",
            "Use +page.server.ts load functions to keep sensitive logic server-side",
            "Configure adapter (adapter-node, adapter-static, adapter-vercel) to match deployment target",
            "Use $lib alias for shared code instead of relative imports",
            "Avoid unnecessary reactive statements that create update cycles",
            "Scope styles in components; use :global() sparingly",
            "Use Vite plugins for asset optimization and environment variables",
            "Write component tests with Vitest and @testing-library/svelte",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building new full-stack apps with SvelteKit",
            "Migrating Sapper applications to SvelteKit",
            "Creating fast, lightweight SPAs with minimal runtime overhead",
            "Implementing SSR or SSG sites with SvelteKit",
            "Building reusable Svelte component libraries",
            "Adding interactivity to server-rendered pages",
            "Optimizing bundle size compared to heavier frameworks",
            "Writing Svelte applications with TypeScript",
        ]

    @property
    def capability_tags(self) -> List[str]:
        return ["patterns", "principles", "testing"]
