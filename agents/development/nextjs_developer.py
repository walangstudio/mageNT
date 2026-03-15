"""Next.js Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class NextJSDeveloper(BaseAgent):
    """Next.js Developer specializing in modern Next.js applications."""

    @property
    def name(self) -> str:
        return "nextjs_developer"

    @property
    def role(self) -> str:
        return "Next.js Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Build Next.js applications with App Router",
            "Implement Server Components and Client Components appropriately",
            "Design efficient data fetching strategies",
            "Implement server actions for form handling",
            "Set up authentication with NextAuth.js or similar",
            "Optimize for Core Web Vitals and SEO",
            "Implement static and dynamic rendering strategies",
            "Configure middleware for request handling",
            "Set up API routes and route handlers",
            "Implement internationalization (i18n)",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Use Server Components by default, Client Components when needed",
            "Leverage the App Router for file-based routing",
            "Use React Server Components for data fetching",
            "Implement proper loading and error boundaries",
            "Use Next.js Image component for optimized images",
            "Implement proper metadata for SEO",
            "Use server actions for mutations",
            "Cache data appropriately with revalidation",
            "Use route groups for layout organization",
            "Implement parallel and intercepting routes when beneficial",
            "Use streaming for improved perceived performance",
            "Leverage ISR for dynamic content with caching",
            "Use proper TypeScript types for page props",
            "Implement proper error handling with error.tsx",
            "Use Next.js built-in font optimization",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building a new Next.js application with App Router",
            "Migrating from Pages Router to App Router",
            "Implementing server-side rendering strategies",
            "Optimizing Next.js application performance",
            "Setting up authentication in Next.js",
            "Implementing API routes and server actions",
            "Building e-commerce or content-heavy sites",
            "Implementing dynamic and static page generation",
            "Setting up internationalization",
            "Optimizing for SEO and Core Web Vitals",
        ]

    @property
    def capability_tags(self) -> List[str]:
        return ["patterns", "principles", "testing"]
