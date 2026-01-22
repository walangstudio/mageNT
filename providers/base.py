"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, List, Optional, Any

from .models import (
    ProviderType,
    ProviderCapabilities,
    Message,
    CompletionResponse,
    StreamChunk,
)


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers.

    All providers must implement this interface to ensure
    consistent behavior across different backends.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize the provider with configuration.

        Args:
            config: Provider-specific configuration from config.yaml
        """
        self.config = config
        self._initialized = False

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return the provider type."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Return provider capabilities."""
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider (e.g., validate API key, test connection).

        Raises:
            ProviderInitializationError: If initialization fails
        """
        pass

    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        **kwargs,
    ) -> CompletionResponse:
        """Generate a completion for the given messages.

        Args:
            messages: List of conversation messages
            system_prompt: Optional system message
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stop_sequences: Sequences that stop generation
            **kwargs: Provider-specific options

        Returns:
            CompletionResponse with the generated text and metadata

        Raises:
            ProviderError: If completion fails
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a completion for the given messages.

        Args:
            messages: List of conversation messages
            system_prompt: Optional system message
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stop_sequences: Sequences that stop generation
            **kwargs: Provider-specific options

        Yields:
            StreamChunk objects with incremental content

        Raises:
            ProviderError: If streaming fails
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in the given text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        pass

    def count_message_tokens(self, messages: List[Message]) -> int:
        """Count total tokens in a list of messages.

        Args:
            messages: List of messages

        Returns:
            Total token count
        """
        total = 0
        for msg in messages:
            total += self.count_tokens(msg.content)
        return total

    async def health_check(self) -> bool:
        """Check if the provider is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self._initialized:
                await self.initialize()
            return True
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(type={self.provider_type.value})"
