"""Optional mememo integration adapter.

Provides persistent project memory, decision tracking, session management,
and context summarization via mememo when available. Falls back gracefully
to no-ops when mememo is not installed.

Initialization is lazy -- the embedding model only loads on first use.
"""

import logging

logger = logging.getLogger(__name__)


def _mememo_importable() -> bool:
    try:
        import mememo.core  # noqa: F401
        return True
    except ImportError:
        return False


class MememoAdapter:
    """Thin adapter over mememo. All methods return None when unavailable."""

    def __init__(self, repo_path: str | None = None):
        self._repo_path = repo_path
        self._importable = _mememo_importable()
        self._initialized = False
        self._memory_manager = None
        self._llm_adapter = None

        if self._importable:
            logger.info("mememo adapter: available (lazy init)")
        else:
            logger.info("mememo adapter: not installed (no-op mode)")

    @property
    def available(self) -> bool:
        return self._importable

    async def _ensure_init(self) -> bool:
        """Lazy initialization -- mirrors mememo's initialize_mememo()."""
        if self._initialized:
            return self._memory_manager is not None
        self._initialized = True

        if not self._importable:
            return False

        try:
            from pathlib import Path
            from mememo.types.config import MemoConfig
            from mememo.core import GitManager, StorageManager, VectorIndex, MemoryManager
            from mememo.embeddings import Embedder
            from mememo.core.llm_adapter import LLMAdapter

            config = MemoConfig.from_env()
            base_dir = Path(config.storage.base_dir)
            base_dir.mkdir(parents=True, exist_ok=True)

            storage_manager = StorageManager(base_dir=base_dir)
            git_manager = GitManager()
            embedder = Embedder(
                model_name=config.embedding.model_name,
                device=config.embedding.device,
                batch_size=config.embedding.batch_size,
            )

            try:
                git_context = await git_manager.detect_context()
                repo_id = git_context.repo.id
                branch = git_context.branch.name
            except Exception:
                repo_id = "default"
                branch = "main"

            vector_index = VectorIndex(
                base_path=base_dir / "vector_index",
                repo_id=repo_id,
                branch=branch,
                dimension=embedder.dimension,
            )

            self._memory_manager = MemoryManager(
                git_manager=git_manager,
                storage_manager=storage_manager,
                embedder=embedder,
                vector_index=vector_index,
                auto_sanitize=config.security.auto_sanitize,
                secrets_detection=config.security.secrets_detection,
            )
            self._llm_adapter = LLMAdapter()
            logger.info("mememo adapter: initialized successfully")
            return True
        except Exception as e:
            logger.warning("mememo adapter init failed: %s", e)
            self._memory_manager = None
            return False

    def _repo_kwargs(self) -> dict:
        if self._repo_path:
            return {"repo_path": self._repo_path}
        return {}

    async def store_memory(
        self,
        content: str,
        type: str = "context",
        tags: list[str] | None = None,
    ) -> str | None:
        if not await self._ensure_init():
            return None
        try:
            from mememo.tools.schemas import StoreMemoryParams
            from mememo.tools.store_memory import store_memory

            params = StoreMemoryParams(
                content=content, type=type, tags=tags, **self._repo_kwargs(),
            )
            resp = await store_memory(params, self._memory_manager)
            return resp.memory_id if resp.success else None
        except Exception as e:
            logger.warning("mememo store_memory failed: %s", e)
            return None

    async def store_decision(
        self,
        problem: str,
        alternatives: list[str],
        chosen: str,
        rationale: str,
        tags: list[str] | None = None,
    ) -> str | None:
        if not await self._ensure_init():
            return None
        try:
            from mememo.tools.schemas import StoreDecisionParams
            from mememo.tools.store_decision import store_decision

            params = StoreDecisionParams(
                problem=problem,
                alternatives=alternatives,
                chosen=chosen,
                rationale=rationale,
                tags=tags,
                **self._repo_kwargs(),
            )
            resp = await store_decision(params, self._memory_manager)
            return resp.memory_id if resp.success else None
        except Exception as e:
            logger.warning("mememo store_decision failed: %s", e)
            return None

    async def recall_context(
        self,
        query: str,
        top_k: int = 5,
        tags: list[str] | None = None,
    ) -> list[dict] | None:
        if not await self._ensure_init():
            return None
        try:
            from mememo.tools.schemas import RecallContextParams
            from mememo.tools.recall_context import recall_context

            params = RecallContextParams(
                query=query, top_k=top_k, tags=tags, **self._repo_kwargs(),
            )
            resp = await recall_context(params, self._memory_manager)
            if not resp.success:
                return None
            return [
                {
                    "content": r.memory.content.text,
                    "type": r.memory.content.type,
                    "tags": r.memory.metadata.tags,
                    "similarity": r.similarity,
                }
                for r in resp.results
            ]
        except Exception as e:
            logger.warning("mememo recall_context failed: %s", e)
            return None

    async def capture(
        self,
        text: str = "",
        hint: str | None = None,
        pre_extracted: list[dict] | None = None,
    ) -> list[dict] | None:
        if not await self._ensure_init():
            return None
        try:
            from mememo.tools.schemas import CaptureParams, PreExtractedMemory
            from mememo.tools.capture import capture

            pre = None
            if pre_extracted:
                pre = [PreExtractedMemory(**item) for item in pre_extracted]

            params = CaptureParams(
                text=text, hint=hint, pre_extracted=pre, **self._repo_kwargs(),
            )
            resp = await capture(params, self._memory_manager, self._llm_adapter)
            if not resp.success:
                return None
            return [
                {"type": e.type, "content": e.content, "memory_id": e.memory_id}
                for e in resp.extracted
            ]
        except Exception as e:
            logger.warning("mememo capture failed: %s", e)
            return None

    async def end_session(
        self,
        summary: str,
        tags: list[str] | None = None,
    ) -> str | None:
        if not await self._ensure_init():
            return None
        try:
            from mememo.tools.schemas import EndSessionParams
            from mememo.tools.end_session import end_session

            params = EndSessionParams(
                summary=summary, tags=tags, **self._repo_kwargs(),
            )
            resp = await end_session(params, self._memory_manager)
            return resp.memory_id if resp.success else None
        except Exception as e:
            logger.warning("mememo end_session failed: %s", e)
            return None

    async def summarize_context(
        self,
        text: str | None = None,
        memory_ids: list[str] | None = None,
        max_tokens: int = 800,
    ) -> str | None:
        if not await self._ensure_init():
            return None
        try:
            from mememo.tools.schemas import SummarizeContextParams
            from mememo.tools.summarize_context import summarize_context

            params = SummarizeContextParams(
                text=text, memory_ids=memory_ids, max_tokens=max_tokens,
                **self._repo_kwargs(),
            )
            resp = await summarize_context(params, self._memory_manager)
            return resp.summary if resp.success else None
        except Exception as e:
            logger.warning("mememo summarize_context failed: %s", e)
            return None


def format_memories(memories: list[dict]) -> str:
    """Format recalled memories into a context block for agent injection."""
    if not memories:
        return ""
    lines = []
    for m in memories:
        prefix = f"[{m.get('type', '?')}]"
        tags = m.get("tags")
        if tags:
            prefix += f" ({', '.join(tags)})"
        lines.append(f"- {prefix} {m['content'][:500]}")
    return "\n".join(lines)
