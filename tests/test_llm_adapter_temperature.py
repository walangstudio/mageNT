"""Temperature resolution in the LLM adapter (no network)."""

from utils.llm_adapter import _get_temperature


def test_code_agent_gets_code_temperature():
    cfg = {"code_agents": ["python_backend"], "code_temperature": 0.1}
    assert _get_temperature(cfg, "python_backend") == 0.1


def test_non_code_agent_gets_default_none():
    cfg = {"code_agents": ["python_backend"], "code_temperature": 0.1}
    assert _get_temperature(cfg, "business_analyst") is None


def test_explicit_agent_override_wins():
    cfg = {
        "code_agents": ["python_backend"],
        "code_temperature": 0.1,
        "agent_temperature": {"python_backend": 0.0},
    }
    assert _get_temperature(cfg, "python_backend") == 0.0


def test_default_temperature_applies_to_uncategorised():
    cfg = {"default_temperature": 0.5}
    assert _get_temperature(cfg, "system_architect") == 0.5


def test_code_temperature_defaults_when_unset():
    cfg = {"code_agents": ["sdet"]}
    assert _get_temperature(cfg, "sdet") == 0.1


def test_empty_config_is_provider_default():
    assert _get_temperature({}, "python_backend") is None


def test_shipped_config_marks_backends_as_code():
    from utils.llm_adapter import _load_providers_config
    cfg = _load_providers_config()
    for agent in ("python_backend", "nodejs_backend", "fullstack_developer"):
        assert _get_temperature(cfg, agent) == cfg.get("code_temperature", 0.1)


# ---- model tier resolution ------------------------------------------------

import pytest

from utils import llm_adapter


@pytest.fixture
def patched_cfg(monkeypatch):
    def _set(cfg):
        monkeypatch.setattr(llm_adapter, "_providers_config", cfg)
        return cfg
    return _set


def test_resolve_model_info_weak(patched_cfg):
    patched_cfg({
        "default_provider": "nvidia",
        "providers": {"nvidia": {"type": "openai_compatible",
                                 "default_model": "meta/llama-3.1-8b-instruct"}},
        "weak_models": ["8b", "7b"],
    })
    info = llm_adapter.resolve_model_info("python_backend")
    assert info["is_weak"] is True and "8b" in info["model"]


def test_resolve_model_info_strong_default(patched_cfg):
    patched_cfg({
        "default_provider": "nvidia",
        "providers": {"nvidia": {"type": "openai_compatible",
                                 "default_model": "qwen/qwen3.5-122b-a10b"}},
        "weak_models": ["8b", "7b"],
    })
    # 122b doesn't match a weak substring -> not weak (conservative default).
    assert llm_adapter.resolve_model_info("python_backend")["is_weak"] is False


def test_resolve_model_info_no_weak_list(patched_cfg):
    patched_cfg({"default_provider": "passthrough"})
    assert llm_adapter.resolve_model_info("python_backend")["is_weak"] is False


def test_passthrough_ordering_invariant():
    # System prompt MUST precede the task; the host caches on the stable prefix.
    out = llm_adapter._dispatch_passthrough("SYSTEM_PERSONA", "DO_THE_TASK", None)
    assert out.index("SYSTEM_PERSONA") < out.index("DO_THE_TASK")
    out2 = llm_adapter._dispatch_passthrough("SYSTEM_PERSONA", "DO_THE_TASK", "CTX")
    assert out2.index("SYSTEM_PERSONA") < out2.index("CTX") < out2.index("DO_THE_TASK")
