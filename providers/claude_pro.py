"""Claude Pro provider - pass-through mode for MCP usage.

This is the default provider that maintains current behavior where
mageNT acts as a prompt engineering layer. The actual LLM (Claude,
GPT, Llama, etc.) is the one calling the MCP tools.
"""

from typing import AsyncIterator, Dict, List, Optional, Any

from .base import BaseLLMProvider
from .models import (
    ProviderType,
    ProviderCapabilities,
    Message,
    MessageRole,
    CompletionResponse,
    StreamChunk,
    TokenUsage,
)


class ClaudeProProvider(BaseLLMProvider):
    """Pass-through provider for MCP tool usage.

    This provider does not make API calls. Instead, it returns
    formatted guidance for the calling LLM to follow.
    This is the default mageNT behavior that works with ANY LLM.
    """

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.CLAUDE_PRO

    @property
    def name(self) -> str:
        return "MCP Pass-Through (Default)"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=False,
            function_calling=False,
            vision=False,
            max_context_tokens=200000,
            max_output_tokens=8192,
            supports_system_message=True,
        )

    async def initialize(self) -> None:
        """No initialization needed for pass-through mode."""
        self._initialized = True

    async def complete(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> CompletionResponse:
        """Return formatted guidance for the calling LLM.

        In pass-through mode, we format the request as guidance
        that the host LLM will follow directly.
        """
        guidance_parts = []

        if system_prompt:
            guidance_parts.append(f"**Expert Instructions:**\n{system_prompt}\n")

        if messages:
            guidance_parts.append("**Context:**")
            for msg in messages:
                if msg.role == MessageRole.USER:
                    guidance_parts.append(f"\n{msg.content}")

        guidance_parts.append(
            "\n\n**Please respond following the expert instructions above.**"
        )

        guidance_text = "\n".join(guidance_parts)

        return CompletionResponse(
            content=guidance_text,
            model="mcp-pass-through",
            provider=self.name,
            usage=TokenUsage(),
            finish_reason="guidance_generated",
        )

    async def stream(
        self, messages: List[Message], **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """Pass-through mode returns guidance in a single chunk."""
        response = await self.complete(messages, **kwargs)
        yield StreamChunk(
            content=response.content,
            index=0,
            is_final=True,
            finish_reason="guidance_generated",
        )

    def count_tokens(self, text: str) -> int:
        """Approximate token count (4 chars per token estimate)."""
        return len(text) // 4
