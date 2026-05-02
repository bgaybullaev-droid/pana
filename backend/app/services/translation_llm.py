"""Shared LLM provider for listing translations.

Supports OpenAI (gpt-4o-mini), Google Gemini, and Ollama (local).
All providers receive the same prompt and return parsed JSON.
"""

import json
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_VALID_PROVIDERS = ("openai", "gemini", "ollama")

# System instruction shared by both providers
_SYSTEM_INSTRUCTION = (
    "You are a real estate listing translator for Uzbekistan. "
    "Translate accurately between Russian, Uzbek, and English. "
    "Return ONLY valid JSON, no markdown fences."
)


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrapping from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return text


def _call_openai(prompt: str) -> dict:
    """Call OpenAI gpt-4o-mini and return parsed JSON."""
    import openai

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = openai.OpenAI(api_key=settings.openai_api_key)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _SYSTEM_INSTRUCTION},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=2000,
    )
    text = _strip_markdown_fences(resp.choices[0].message.content)
    return json.loads(text)


def _call_gemini(prompt: str) -> dict:
    """Call Google Gemini and return parsed JSON."""
    import google.generativeai as genai

    api_key = settings.gemini_api_key
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        "gemini-2.5-flash-lite",
        system_instruction=_SYSTEM_INSTRUCTION,
    )
    resp = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=2000,
        ),
    )
    text = _strip_markdown_fences(resp.text)
    return json.loads(text)


def _call_ollama(prompt: str) -> dict:
    """Call local Ollama and return parsed JSON."""
    import openai

    base_url = getattr(settings, "ollama_base_url", "http://localhost:11434")
    model = getattr(settings, "ollama_model", "qwen2.5:7b")

    client = openai.OpenAI(base_url=f"{base_url}/v1", api_key="ollama")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_INSTRUCTION},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=2000,
    )
    text = _strip_markdown_fences(resp.choices[0].message.content)
    return json.loads(text)


def call_translation_llm(prompt: str, provider: Optional[str] = None) -> dict:
    """Call the configured LLM provider and return parsed JSON.

    Args:
        prompt: The translation prompt.
        provider: "openai", "gemini", or "ollama". Falls back to settings.translation_provider.

    Returns:
        Parsed JSON dict with translated fields.

    Raises:
        ValueError: If provider is not one of the valid options.
        RuntimeError: If the selected provider's API key is not configured.
        json.JSONDecodeError: If the LLM response is not valid JSON.
    """
    provider = provider or settings.translation_provider
    provider = provider.lower().strip()

    if provider not in _VALID_PROVIDERS:
        raise ValueError(
            f"Invalid translation provider: {provider!r}. "
            f"Must be one of: {', '.join(_VALID_PROVIDERS)}"
        )

    logger.debug(f"[TRANSLATE] Using provider: {provider}")

    if provider == "openai":
        return _call_openai(prompt)
    elif provider == "gemini":
        return _call_gemini(prompt)
    else:
        return _call_ollama(prompt)
