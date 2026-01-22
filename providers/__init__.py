"""LLM Providers module.

Provides a unified interface for different LLM backends.
The default ClaudeProProvider is a pass-through that works with ANY LLM
calling the MCP tools.

Optional API providers can be enabled for advanced use cases where
the MCP server itself needs to make LLM calls.
"""

from typing import Dict, Type, Optional, List, Any

from .base import BaseLLMProvider
from .models import (
    ProviderType,
    ProviderCapabilities,
    Message,
    MessageRole,
    CompletionRequest,
    CompletionResponse,
    StreamChunk,
    TokenUsage,
)
from .exceptions import (
    LLMProviderError,
    ProviderInitializationError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    TokenLimitExceededError,
    InvalidRequestError,
)
from .claude_pro import ClaudeProProvider


class ProviderRegistry:
    """Registry for LLM providers with factory methods."""

    _providers: Dict[ProviderType, Type[BaseLLMProvider]] = {
        ProviderType.CLAUDE_PRO: ClaudeProProvider,
    }

    # Lazy-loaded providers (only imported when needed)
    _lazy_providers: Dict[ProviderType, str] = {
        ProviderType.ANTHROPIC: "anthropic",
        ProviderType.OPENAI: "openai",
        ProviderType.OLLAMA: "local",
        ProviderType.LMSTUDIO: "local",
        ProviderType.GROQ: "groq",
        ProviderType.TOGETHER: "together",
    }

    @classmethod
    def get_provider_class(cls, provider_type: ProviderType) -> Type[BaseLLMProvider]:
        """Get the provider class for a given type."""
        if provider_type in cls._providers:
            return cls._providers[provider_type]

        if provider_type in cls._lazy_providers:
            module_name = cls._lazy_providers[provider_type]
            try:
                if module_name == "anthropic":
                    from .anthropic import AnthropicProvider
                    cls._providers[provider_type] = AnthropicProvider
                elif module_name == "openai":
                    from .openai import OpenAIProvider
                    cls._providers[provider_type] = OpenAIProvider
                elif module_name == "local":
                    from .local import LocalProvider
                    cls._providers[provider_type] = LocalProvider
                elif module_name == "groq":
                    from .groq import GroqProvider
                    cls._providers[provider_type] = GroqProvider
                elif module_name == "together":
                    from .together import TogetherProvider
                    cls._providers[provider_type] = TogetherProvider
                return cls._providers[provider_type]
            except ImportError as e:
                raise ProviderInitializationError(
                    f"Provider {provider_type.value} requires additional dependencies: {e}",
                    provider_type.value,
                )

        raise ValueError(f"Unknown provider type: {provider_type}")

    @classmethod
    def create_provider(
        cls, provider_type: ProviderType, config: Dict[str, Any]
    ) -> BaseLLMProvider:
        """Factory method to create a provider instance."""
        provider_class = cls.get_provider_class(provider_type)
        return provider_class(config)

    @classmethod
    def list_available_providers(cls) -> List[str]:
        """List all registered provider types."""
        all_providers = list(cls._providers.keys()) + list(cls._lazy_providers.keys())
        return [p.value for p in set(all_providers)]

    @classmethod
    def register_provider(
        cls, provider_type: ProviderType, provider_class: Type[BaseLLMProvider]
    ) -> None:
        """Register a new provider type."""
        cls._providers[provider_type] = provider_class


__all__ = [
    # Base classes
    "BaseLLMProvider",
    "ProviderType",
    "ProviderCapabilities",
    # Models
    "Message",
    "MessageRole",
    "CompletionRequest",
    "CompletionResponse",
    "StreamChunk",
    "TokenUsage",
    # Exceptions
    "LLMProviderError",
    "ProviderInitializationError",
    "ProviderAuthenticationError",
    "ProviderRateLimitError",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    "TokenLimitExceededError",
    "InvalidRequestError",
    # Registry
    "ProviderRegistry",
    # Concrete providers
    "ClaudeProProvider",
]
