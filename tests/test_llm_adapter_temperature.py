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
