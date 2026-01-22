"""Custom exceptions for LLM providers."""

from typing import Optional


class LLMProviderError(Exception):
    """Base exception for all provider errors."""

    def __init__(self, message: str, provider: str, retriable: bool = False):
        super().__init__(message)
        self.provider = provider
        self.retriable = retriable


class ProviderInitializationError(LLMProviderError):
    """Raised when provider initialization fails."""

    def __init__(self, message: str, provider: str):
        super().__init__(message, provider, retriable=False)


class ProviderAuthenticationError(LLMProviderError):
    """Raised when API authentication fails."""

    def __init__(self, message: str, provider: str):
        super().__init__(message, provider, retriable=False)


class ProviderRateLimitError(LLMProviderError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, provider: str, retry_after: Optional[int] = None):
        super().__init__(message, provider, retriable=True)
        self.retry_after = retry_after


class ProviderTimeoutError(LLMProviderError):
    """Raised when request times out."""

    def __init__(self, message: str, provider: str):
        super().__init__(message, provider, retriable=True)


class ProviderUnavailableError(LLMProviderError):
    """Raised when provider is unavailable."""

    def __init__(self, message: str, provider: str):
        super().__init__(message, provider, retriable=True)


class TokenLimitExceededError(LLMProviderError):
    """Raised when token limit is exceeded."""

    def __init__(
        self, message: str, provider: str, requested_tokens: int, max_tokens: int
    ):
        super().__init__(message, provider, retriable=False)
        self.requested_tokens = requested_tokens
        self.max_tokens = max_tokens


class InvalidRequestError(LLMProviderError):
    """Raised for invalid request parameters."""

    def __init__(self, message: str, provider: str):
        super().__init__(message, provider, retriable=False)
