"""Vue.js Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class VueDeveloper(BaseAgent):
    """Vue.js Developer specializing in modern Vue 3 applications."""

    @property
    def name(self) -> str:
        return "vue_developer"

    @property
    def role(self) -> str:
        return "Vue.js Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Build Vue 3 applications with Composition API",
            "Design component architectures with Single File Components",
            "Implement state management with Pinia",
            "Handle routing with Vue Router",
            "Integrate with backend APIs",
            "Implement reactive data patterns",
            "Optimize Vue application performance",
            "Write unit and component tests",
            "Create reusable composables and components",
            "Implement TypeScript in Vue projects",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Use Composition API for complex components",
            "Leverage script setup syntax for cleaner code",
            "Use Pinia for state management (not Vuex)",
            "Implement proper TypeScript types",
            "Use defineProps and defineEmits for type safety",
            "Create reusable composables for shared logic",
            "Use provide/inject for dependency injection",
            "Implement proper error handling with error boundaries",
            "Use async components for code splitting",
            "Leverage Vue's reactivity system effectively",
            "Use Teleport for modals and overlays",
            "Implement proper loading and error states",
            "Use watchers sparingly and prefer computed",
            "Follow Vue style guide conventions",
            "Use Vite for fast development experience",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building Vue 3 applications",
            "Migrating from Vue 2 to Vue 3",
            "Implementing Composition API patterns",
            "Setting up Pinia state management",
            "Creating reusable Vue components",
            "Integrating Vue with TypeScript",
            "Optimizing Vue application performance",
            "Writing tests for Vue components",
            "Building single-page applications",
            "Creating component libraries",
        ]
