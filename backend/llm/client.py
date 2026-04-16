import time

from config import settings
from logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Provider-specific call functions
# ---------------------------------------------------------------------------

def _call_anthropic(prompt: str, system: str, model: str, max_tokens: int) -> str:
    import anthropic
    client = getattr(_call_anthropic, "_client", None)
    if client is None:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=3)
        _call_anthropic._client = client
    messages = [{"role": "user", "content": prompt}]
    kwargs = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    return response.content[0].text.strip(), response.usage.output_tokens


def _call_openai(prompt: str, system: str, model: str, max_tokens: int) -> str:
    import openai
    client = getattr(_call_openai, "_client", None)
    if client is None:
        client = openai.OpenAI(api_key=settings.openai_api_key)
        _call_openai._client = client
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model=model, max_tokens=max_tokens, messages=messages,
    )
    choice = response.choices[0].message.content.strip()
    return choice, response.usage.completion_tokens


# ---------------------------------------------------------------------------
# Provider dispatch
# ---------------------------------------------------------------------------

_PROVIDERS = {"anthropic": _call_anthropic, "openai": _call_openai}

_provider = settings.llm_provider.lower()
if _provider not in _PROVIDERS:
    raise ValueError(
        f"Unsupported LLM_PROVIDER={settings.llm_provider!r}. "
        f"Choose from: {', '.join(_PROVIDERS)}"
    )
_call = _PROVIDERS[_provider]
log.info("LLM provider: %s", _provider)


# ---------------------------------------------------------------------------
# Public API (unchanged signatures)
# ---------------------------------------------------------------------------

def fast_chat(prompt: str, system: str = "") -> str:
    """Call the fast (Haiku / GPT-4o-mini) model. Use for routing, extraction, grading."""
    model = settings.llm_fast_model
    log.debug("LLM fast call | model=%s | prompt_len=%d", model, len(prompt))
    t0 = time.perf_counter()
    text, out_tokens = _call(prompt, system, model, 1024)
    elapsed = time.perf_counter() - t0
    log.debug(
        "LLM fast done | model=%s | out_tokens=%d | elapsed=%.2fs",
        model, out_tokens, elapsed,
    )
    return text


def strong_chat(prompt: str, system: str = "") -> str:
    """Call the strong (Sonnet / GPT-4o) model. Use for grounded answer generation."""
    model = settings.llm_strong_model
    log.debug("LLM strong call | model=%s | prompt_len=%d", model, len(prompt))
    t0 = time.perf_counter()
    text, out_tokens = _call(prompt, system, model, 2048)
    elapsed = time.perf_counter() - t0
    log.info(
        "LLM strong done | model=%s | out_tokens=%d | elapsed=%.2fs",
        model, out_tokens, elapsed,
    )
    return text
