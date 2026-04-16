import time

import anthropic

from config import settings
from logger import get_logger

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
log = get_logger(__name__)


def fast_chat(prompt: str, system: str = "") -> str:
    """Call the fast (Haiku) model. Use for routing, extraction, grading."""
    model = settings.llm_fast_model
    log.debug("LLM fast call | model=%s | prompt_len=%d", model, len(prompt))
    t0 = time.perf_counter()
    messages = [{"role": "user", "content": prompt}]
    kwargs = {"model": model, "max_tokens": 1024, "messages": messages}
    if system:
        kwargs["system"] = system
    response = _client.messages.create(**kwargs)
    elapsed = time.perf_counter() - t0
    out_tokens = response.usage.output_tokens
    log.debug(
        "LLM fast done | model=%s | out_tokens=%d | elapsed=%.2fs",
        model, out_tokens, elapsed,
    )
    return response.content[0].text.strip()


def strong_chat(prompt: str, system: str = "") -> str:
    """Call the strong (Sonnet) model. Use for grounded answer generation."""
    model = settings.llm_strong_model
    log.debug("LLM strong call | model=%s | prompt_len=%d", model, len(prompt))
    t0 = time.perf_counter()
    messages = [{"role": "user", "content": prompt}]
    kwargs = {"model": model, "max_tokens": 2048, "messages": messages}
    if system:
        kwargs["system"] = system
    response = _client.messages.create(**kwargs)
    elapsed = time.perf_counter() - t0
    out_tokens = response.usage.output_tokens
    log.info(
        "LLM strong done | model=%s | out_tokens=%d | elapsed=%.2fs",
        model, out_tokens, elapsed,
    )
    return response.content[0].text.strip()
