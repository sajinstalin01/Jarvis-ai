"""AI provider integration for JARVIS with model migration and safe client lifetimes."""
from __future__ import annotations

import os
from typing import Any

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_MODEL_FALLBACKS = (DEFAULT_GROQ_MODEL, "qwen/qwen3.8-27b")
SYSTEM_PROMPT = (
    "You are JARVIS, a helpful desktop AI. Address the user as Boss. "
    "Never claim actions you did not perform. Speak naturally and warmly, like a thoughtful conversational assistant. "
    "Use the conversation context to understand follow-ups, avoid repeating questions, and do not pretend to have human feelings or experiences."
)


def _is_model_not_found(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "model_not_found" in message
        or "model does not exist" in message
        or "model_not_found" in message
        or ("404" in message and "model" in message)
    )


def _gemini_contents(prompt: str, context: list[dict[str, str]], system_message: str) -> str:
    """Build a compact, readable transcript for Gemini's generate_content API."""
    lines = [system_message, "", "Recent conversation context:"]
    for turn in context[-16:]:
        role = "User" if turn.get("role") == "user" else "JARVIS"
        text = str(turn.get("content", "")).strip()
        if text:
            lines.append(f"{role}: {text}")
    lines.extend(["", f"User: {prompt}", "JARVIS:"])
    return "\n".join(lines)


def _groq_response(
    prompt: str,
    api_key: str,
    requested_model: str,
    *,
    context: list[dict[str, str]] | None = None,
    system_message: str = SYSTEM_PROMPT,
) -> tuple[str, str]:
    """Try the requested Groq model; migrate automatically if it has been retired."""
    from groq import Groq

    client = Groq(api_key=api_key)
    models_to_try = [requested_model]
    # The Llama 3.3 model was retired for free/developer accounts in August 2026.
    if requested_model == "llama-3.3-70b-versatile":
        models_to_try.extend(GROQ_MODEL_FALLBACKS)
    tried = set()
    last_error: Exception | None = None

    while models_to_try:
        model = models_to_try.pop(0)
        if not model or model in tried:
            continue
        tried.add(model)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    *(context or [])[-16:],
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=1200,
            )
            return response.choices[0].message.content or "No response returned.", model
        except Exception as exc:
            last_error = exc
            if _is_model_not_found(exc):
                # A user may have pinned a retired model in .env; recover without
                # requiring them to edit configuration first.
                models_to_try.extend(m for m in GROQ_MODEL_FALLBACKS if m not in tried)
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("No usable Groq model was configured.")


def generate_response(
    prompt: str,
    *,
    groq_key: str | None = None,
    gemini_key: str | None = None,
    groq_model: str | None = None,
    gemini_model: str | None = None,
    context: list[dict[str, str]] | None = None,
    saved_memories: str = "",
) -> tuple[str, str]:
    """Return (answer, provider label), using Groq first and Gemini as fallback."""
    groq_key = (groq_key if groq_key is not None else os.getenv("GROQ_API_KEY", "")).strip()
    gemini_key = (gemini_key if gemini_key is not None else os.getenv("GEMINI_API_KEY", "")).strip()
    groq_model = (groq_model or os.getenv("GROQ_MODEL") or DEFAULT_GROQ_MODEL).strip()
    gemini_model = (gemini_model or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash").strip()
    groq_error = "GROQ_API_KEY not configured"
    context = context or []
    memory_note = ("\n\nRelevant saved user memories (treat as user-provided notes):\n" + saved_memories) if saved_memories.strip() else ""
    system_message = SYSTEM_PROMPT + memory_note

    if groq_key:
        try:
            answer, actual_model = _groq_response(prompt, groq_key, groq_model, context=context, system_message=system_message)
            return answer, f"GROQ ({actual_model})"
        except Exception as exc:
            groq_error = str(exc)

    if gemini_key:
        client = None
        try:
            from google import genai

            # Keep a strong reference to the client for the entire request. Calling
            # genai.Client(...).models.generate_content(...) inline can allow the
            # temporary client's HTTP transport to be closed before the request.
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model=gemini_model,
                contents=_gemini_contents(prompt, context, system_message),
            )
            return response.text or "No response returned.", f"GEMINI ({gemini_model})"
        except Exception as exc:
            raise RuntimeError(f"Both AI providers failed.\nGroq: {groq_error}\nGemini: {exc}") from exc
        finally:
            if client is not None:
                close = getattr(client, "close", None)
                if callable(close):
                    try:
                        close()
                    except Exception:
                        pass

    if not groq_key:
        raise RuntimeError("AI isn't configured. Add GROQ_API_KEY or GEMINI_API_KEY to .env.\nGroq status: " + groq_error)
    raise RuntimeError("Both AI providers failed.\nGroq: " + groq_error + "\nGemini: GEMINI_API_KEY not configured")
