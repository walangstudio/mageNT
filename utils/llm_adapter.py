"""LLM adapter for optional direct agent dispatch."""

import os
from pathlib import Path

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


def dispatch(agent_name: str, system_prompt: str, task: str, context=None) -> str:
    cfg = _load_providers_config()
    provider = cfg.get('agent_providers', {}).get(agent_name) or cfg.get('default_provider', 'passthrough')
    model = _get_model(cfg, provider, agent_name)

    if provider == 'anthropic':
        return _dispatch_anthropic(model, system_prompt, task, context, cfg)
    if provider == 'ollama':
        return _dispatch_ollama(model, system_prompt, task, context, cfg)
    provider_cfg = cfg.get('providers', {}).get(provider, {})
    if provider_cfg.get('type') == 'openai_compatible':
        return _dispatch_openai_compat(model, system_prompt, task, context, provider, provider_cfg)
    return _dispatch_passthrough(system_prompt, task, context)


def _get_model(cfg, provider, agent_name):
    return (
        cfg.get('model_per_agent', {}).get(agent_name) or
        cfg.get('providers', {}).get(provider, {}).get('default_model') or
        _DEFAULT_MODELS.get(provider)
    )


def _get_api_key(provider, provider_cfg):
    return os.environ.get(f'{provider.upper()}_API_KEY') or provider_cfg.get('api_key') or None


def _dispatch_passthrough(system_prompt, task, context):
    body = f"{context}\n\n---\n\nTask: {task}" if context else task
    return f"{system_prompt}\n\n---\n\n{body}"


def _dispatch_anthropic(model, system_prompt, task, context, cfg):
    api_key = _get_api_key('anthropic', cfg.get('providers', {}).get('anthropic', {}))
    if not api_key:
        return _dispatch_passthrough(system_prompt, task, context)
    content = f"{context}\n\n---\n\nTask: {task}" if context else task
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(model=model, max_tokens=8096, system=system_prompt,
                                      messages=[{"role": "user", "content": content}])
        return resp.content[0].text
    except Exception:
        return _dispatch_passthrough(system_prompt, task, context)


def _dispatch_ollama(model, system_prompt, task, context, cfg):
    base_url = cfg.get('providers', {}).get('ollama', {}).get('base_url', 'http://localhost:11434')
    prompt = f"{system_prompt}\n\n{context}\n\n---\n\nTask: {task}" if context else f"{system_prompt}\n\n{task}"
    try:
        import requests
        resp = requests.post(f"{base_url}/api/generate",
                             json={"model": model, "prompt": prompt, "stream": False}, timeout=120)
        resp.raise_for_status()
        return resp.json()["response"]
    except Exception:
        return _dispatch_passthrough(system_prompt, task, context)


def _dispatch_openai_compat(model, system_prompt, task, context, provider, provider_cfg):
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
    try:
        import requests
        resp = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content']
    except Exception:
        return _dispatch_passthrough(system_prompt, task, context)
