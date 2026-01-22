"""Data models for LLM providers."""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from enum import Enum
from datetime import datetime


class MessageRole(Enum):
    """Message roles in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ProviderType(Enum):
    """Supported LLM provider types."""
    CLAUDE_PRO = "claude_pro"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    GROQ = "groq"
    TOGETHER = "together"


@dataclass
class ProviderCapabilities:
    """Describes what a provider can do."""
    streaming: bool = True
    function_calling: bool = False
    vision: bool = False
    max_context_tokens: int = 8192
    max_output_tokens: int = 4096
    supports_system_message: bool = True


@dataclass
class Message:
    """A single message in a conversation."""
    role: MessageRole
    content: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        d = {"role": self.role.value, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d

    @classmethod
    def user(cls, content: str) -> "Message":
        """Create a user message."""
        return cls(role=MessageRole.USER, content=content)

    @classmethod
    def assistant(cls, content: str) -> "Message":
        """Create an assistant message."""
        return cls(role=MessageRole.ASSISTANT, content=content)

    @classmethod
    def system(cls, content: str) -> "Message":
        """Create a system message."""
        return cls(role=MessageRole.SYSTEM, content=content)


@dataclass
class TokenUsage:
    """Token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens
        )


@dataclass
class CompletionResponse:
    """Response from a completion request."""
    content: str
    model: str
    provider: str
    usage: TokenUsage
    finish_reason: str = "stop"
    created_at: datetime = field(default_factory=datetime.now)
    raw_response: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "usage": {
                "prompt_tokens": self.usage.prompt_tokens,
                "completion_tokens": self.usage.completion_tokens,
                "total_tokens": self.usage.total_tokens
            },
            "finish_reason": self.finish_reason,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class StreamChunk:
    """A chunk of streamed content."""
    content: str
    index: int
    is_final: bool = False
    finish_reason: Optional[str] = None
    usage: Optional[TokenUsage] = None


@dataclass
class CompletionRequest:
    """Unified request structure for completions."""
    messages: List[Message]
    system_prompt: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    stop_sequences: Optional[List[str]] = None
    stream: bool = False
    provider_override: Optional[str] = None
    fallback_enabled: bool = True
    request_id: Optional[str] = None
    agent_name: Optional[str] = None
