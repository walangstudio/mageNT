"""LLM adapter for optional direct agent dispatch.

Two entry points:

* ``dispatch(...)``      → returns ``str``, kept for backwards compatibility.
* ``dispatch_full(...)`` → returns ``(text, usage)`` tuple. Used by the Phase 7
  ``spec_pipeline`` so per-call token / cost is captured into ``cost.json``.

When ``response_schema`` is supplied, OpenAI-compatible providers (LM Studio,
NVIDIA NIM, OpenAI proper) get ``response_format={"type":"json_schema",...}`` —
the model is grammar-constrained to emit conforming JSON, which dramatically
lifts parseability on mid-size local models (Llama-8B, Mistral, Qwen-14B).
Anthropic gets the schema injected as a tool ``input_schema`` via the
``tool_use`` workaround (Sonnet 4.6+ honours it).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_DEFAULT_MODELS = {
    'anthropic': 'claude-sonnet-4-6',
    'ollama': 'llama3.1',
    'openai': 'gpt-4o',
}

_providers_config = None


def _load_providers_config():
    global _providers_config
    if _providers_config is not None:
        return _providers_config

    import yaml

    env_path = os.environ.get('MAGENT_PROVIDERS')
    cwd_path = Path.cwd() / 'providers.yaml'
    default_path = Path(__file__).parent.parent / 'config' / 'providers.yaml'

    resolved = (
        Path(env_path) if env_path and Path(env_path).exists()
        else cwd_path if cwd_path.exists()
        else default_path
    )

    try:
        with open(resolved, 'r', encoding='utf-8') as f:
            _providers_config = yaml.safe_load(f) or {}
    except Exception:
        _providers_config = {}

    return _providers_config


# ---------- public API -----------------------------------------------------

def dispatch(agent_name: str, system_prompt: str, task: str, context=None) -> str:
    """Sync dispatch returning text only. Kept for backwards compatibility."""
    text, _ = dispatch_full(agent_name, system_prompt, task, context=context)
    return text


def dispatch_full(
    agent_name: str,
    system_prompt: str,
    task: str,
    context: Optional[str] = None,
    response_schema: Optional[Dict[str, Any]] = None,
    schema_name: str = "Response",
    temperature: Optional[float] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Sync dispatch returning ``(text, usage_dict)``.

    ``response_schema``: a JSON-Schema dict (as produced by
    ``Pydantic.BaseModel.model_json_schema()``). When set, OpenAI-compatible
    providers receive grammar-constrained output. ``usage_dict`` contains
    provider-reported token counts when available; ``{}`` otherwise.

    ``temperature``: explicit override; when ``None`` it is resolved from the
    providers config (``_get_temperature``). Best-of-N candidate generation
    passes a higher value here to get sampling diversity.
    """
    cfg = _load_providers_config()
    provider = cfg.get('agent_providers', {}).get(agent_name) or cfg.get('default_provider', 'passthrough')
    model = _get_model(cfg, provider, agent_name)
    if temperature is None:
        temperature = _get_temperature(cfg, agent_name)

    if provider == 'anthropic':
        return _dispatch_anthropic(model, system_prompt, task, context, cfg,
                                     response_schema, schema_name, temperature)
    if provider == 'ollama':
        return _dispatch_ollama(model, system_prompt, task, context, cfg,
                                  response_schema, temperature)
    provider_cfg = cfg.get('providers', {}).get(provider, {})
    if provider_cfg.get('type') == 'openai_compatible':
        return _dispatch_openai_compat(model, system_prompt, task, context,
                                          provider, provider_cfg,
                                          response_schema, schema_name, temperature)
    return _dispatch_passthrough(system_prompt, task, context), {}


# ---------- internals ------------------------------------------------------

def _get_model(cfg, provider, agent_name):
    return (
        cfg.get('model_per_agent', {}).get(agent_name) or
        cfg.get('providers', {}).get(provider, {}).get('default_model') or
        _DEFAULT_MODELS.get(provider)
    )


def _get_temperature(cfg, agent_name):
    """Resolve sampling temperature for an agent (None = provider default).

    Precedence: explicit ``agent_temperature[agent]`` > ``code_temperature`` for
    agents listed in ``code_agents`` > global ``default_temperature`` > None.
    Code/test generation wants a low temperature (higher pass@1); design and
    ideation agents are left warm.
    """
    at = cfg.get('agent_temperature') or {}
    if agent_name in at:
        return at[agent_name]
    code_agents = cfg.get('code_agents') or []
    if agent_name in code_agents:
        ct = cfg.get('code_temperature')
        if ct is not None:
            return ct
        # code_temperature unset: fall to default_temperature, else a cool 0.1.
        return cfg.get('default_temperature', 0.1)
    return cfg.get('default_temperature', None)


def _get_api_key(provider, provider_cfg):
    return os.environ.get(f'{provider.upper()}_API_KEY') or provider_cfg.get('api_key') or None


def _dispatch_passthrough(system_prompt, task, context):
    body = f"{context}\n\n---\n\nTask: {task}" if context else task
    return f"{system_prompt}\n\n---\n\n{body}"


def _dispatch_anthropic(model, system_prompt, task, context, cfg,
                          response_schema, schema_name, temperature=None):
    api_key = _get_api_key('anthropic', cfg.get('providers', {}).get('anthropic', {}))
    if not api_key:
        return _dispatch_passthrough(system_prompt, task, context), {}
    content = f"{context}\n\n---\n\nTask: {task}" if context else task
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        kwargs = dict(model=model, max_tokens=8096, system=system_prompt,
                       messages=[{"role": "user", "content": content}])
        if temperature is not None:
            kwargs["temperature"] = temperature
        # Schema-constrained output via tool-use trick: define a single tool
        # whose input_schema IS the desired output, then force it. Anthropic
        # SDK 0.40+ supports this idiom; older SDKs ignore it gracefully.
        if response_schema:
            kwargs["tools"] = [{
                "name": schema_name.lower(),
                "description": f"Emit the {schema_name} response object.",
                "input_schema": response_schema,
            }]
            kwargs["tool_choice"] = {"type": "tool", "name": schema_name.lower()}
        resp = client.messages.create(**kwargs)
        # Extract usage
        usage = {}
        if hasattr(resp, "usage"):
            u = resp.usage
            usage = {"input_tokens": getattr(u, "input_tokens", 0),
                      "output_tokens": getattr(u, "output_tokens", 0)}
        # Extract text — either from a tool_use block (schema mode) or text block.
        for block in resp.content:
            if getattr(block, "type", "") == "tool_use" and getattr(block, "input", None):
                import json as _json
                return _json.dumps(block.input), usage
            if hasattr(block, "text"):
                return block.text, usage
        return "", usage
    except Exception:
        return _dispatch_passthrough(system_prompt, task, context), {}


def _dispatch_ollama(model, system_prompt, task, context, cfg, response_schema,
                       temperature=None):
    base_url = cfg.get('providers', {}).get('ollama', {}).get('base_url', 'http://localhost:11434')
    prompt = (
        f"{system_prompt}\n\n{context}\n\n---\n\nTask: {task}"
        if context else f"{system_prompt}\n\n{task}"
    )
    try:
        import requests
        payload = {"model": model, "prompt": prompt, "stream": False}
        if temperature is not None:
            payload["options"] = {"temperature": temperature}
        # Ollama supports JSON-schema constraint via `format` since v0.5.
        if response_schema:
            payload["format"] = response_schema
        resp = requests.post(f"{base_url}/api/generate", json=payload, timeout=120)
        resp.raise_for_status()
        body = resp.json()
        usage = {}
        # Ollama returns prompt_eval_count + eval_count when available.
        if "prompt_eval_count" in body or "eval_count" in body:
            usage = {
                "input_tokens": body.get("prompt_eval_count", 0),
                "output_tokens": body.get("eval_count", 0),
            }
        return body.get("response", ""), usage
    except Exception:
        return _dispatch_passthrough(system_prompt, task, context), {}


def _dispatch_openai_compat(model, system_prompt, task, context, provider,
                              provider_cfg, response_schema, schema_name,
                              temperature=None):
    api_key = _get_api_key(provider, provider_cfg)
    base_url = provider_cfg.get('base_url', 'https://api.openai.com/v1').rstrip('/')
    content = f"{context}\n\n---\n\nTask: {task}" if context else task
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    payload = {
        'model': model,
        'max_tokens': 8096,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': content},
        ],
    }
    if temperature is not None:
        payload['temperature'] = temperature
    if response_schema:
        # OpenAI / LM Studio / NVIDIA NIM all accept this shape. Strict mode
        # forces grammar-constrained output — the model literally cannot emit
        # non-conforming tokens. Only schemas WITHOUT $ref/anyOf complications
        # are accepted in strict mode by some providers; we set strict but the
        # try/except below catches the 400 and retries without it.
        payload['response_format'] = {
            'type': 'json_schema',
            'json_schema': {
                'name': schema_name,
                'schema': response_schema,
                'strict': True,
            },
        }
    # Local LLMs can be slow on first hit (JIT model load) or on large prompts.
    # 600s is the right ceiling — beyond that the request is genuinely stuck.
    timeout = int(os.environ.get("MAGENT_LLM_TIMEOUT", "600"))
    # MAGENT_INSECURE_SSL=1 bypasses TLS verification — needed when an
    # antivirus / corporate proxy MITM-intercepts HTTPS (e.g. Avast).
    verify_ssl = os.environ.get("MAGENT_INSECURE_SSL", "").lower() not in ("1", "true", "yes")
    try:
        import requests
        resp = requests.post(f"{base_url}/chat/completions",
                              json=payload, headers=headers,
                              timeout=timeout, verify=verify_ssl)
        # Some local servers reject strict mode; retry without it.
        if resp.status_code == 400 and response_schema:
            payload['response_format'] = {'type': 'json_object'}
            resp = requests.post(f"{base_url}/chat/completions",
                                  json=payload, headers=headers,
                                  timeout=timeout, verify=verify_ssl)
        resp.raise_for_status()
        body = resp.json()
        usage_raw = body.get('usage') or {}
        usage = {
            "input_tokens": usage_raw.get("prompt_tokens", 0),
            "output_tokens": usage_raw.get("completion_tokens", 0),
        }
        text = body['choices'][0]['message'].get('content') or ""
        return text, usage
    except Exception as e:
        # Surface the real failure tagged so the retry loop sees it as a
        # validation-failure-equivalent (the response IS the error message).
        # Returning passthrough echo silently is what masked LM Studio
        # timeouts as "agent output invalid" before.
        err_payload = (
            f"<llm_dispatch_error provider={provider} model={model}>"
            f"{type(e).__name__}: {str(e)[:300]}"
            f"</llm_dispatch_error>"
        )
        return err_payload, {"error": str(e)[:200]}
