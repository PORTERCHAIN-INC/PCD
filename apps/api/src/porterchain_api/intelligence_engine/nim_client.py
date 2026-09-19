"""NVIDIA NIM OpenAI-compatible chat client (free-tier / self-hosted NIM).

Not on the pay path. Used by intelligence_engine.copilot behind phase2 flags.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from porterchain_shared.config.settings import get_platform_settings

logger = logging.getLogger(__name__)

# Simple process-local circuit: open after consecutive failures, cool down briefly.
_fail_streak = 0
_circuit_open_until = 0.0
_CIRCUIT_FAILS = 3
_CIRCUIT_COOLDOWN_S = 45.0
_RETRYABLE = {408, 429, 500, 502, 503, 504}


def nim_configured() -> bool:
    settings = get_platform_settings()
    return bool((getattr(settings, "nvidia_api_key", "") or "").strip())


def nim_status() -> dict[str, Any]:
    """Ops-facing health snapshot (no secrets)."""
    settings = get_platform_settings()
    configured = bool((getattr(settings, "nvidia_api_key", "") or "").strip())
    open_now = time.monotonic() < _circuit_open_until
    return {
        "configured": configured,
        "provider": "nvidia_nim",
        "model": (getattr(settings, "nvidia_model", None) or "openai/gpt-oss-20b"),
        "api_base": (
            getattr(settings, "nvidia_api_base", None) or "https://integrate.api.nvidia.com/v1"
        ),
        "circuit_open": open_now,
        "fail_streak": _fail_streak,
    }


def _record_success() -> None:
    global _fail_streak, _circuit_open_until
    _fail_streak = 0
    _circuit_open_until = 0.0


def _record_failure() -> None:
    global _fail_streak, _circuit_open_until
    _fail_streak += 1
    if _fail_streak >= _CIRCUIT_FAILS:
        _circuit_open_until = time.monotonic() + _CIRCUIT_COOLDOWN_S
        logger.warning("NIM circuit open for %.0fs after %s failures", _CIRCUIT_COOLDOWN_S, _fail_streak)


def chat_completion(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 800,
    timeout_s: float = 30.0,
    json_object: bool = True,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Call NVIDIA NIM (or compatible) chat completions API.

    Returns ``{content, model, prompt_tokens, completion_tokens, latency_ms}``.
    Raises ``ValueError`` when not configured; ``RuntimeError`` on HTTP failure
    or open circuit.
    """
    if time.monotonic() < _circuit_open_until:
        raise RuntimeError("nvidia_nim_circuit_open")

    settings = get_platform_settings()
    api_key = (getattr(settings, "nvidia_api_key", "") or "").strip()
    if not api_key:
        raise ValueError("nvidia_api_key_missing")

    base = (
        getattr(settings, "nvidia_api_base", None)
        or "https://integrate.api.nvidia.com/v1"
    ).rstrip("/")
    use_model = (
        model
        or getattr(settings, "nvidia_model", None)
        or "openai/gpt-oss-20b"
    ).strip()

    payload: dict[str, Any] = {
        "model": use_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_object:
        # OpenAI-compatible; NIM ignores unknown fields on older builds.
        payload["response_format"] = {"type": "json_object"}

    started = time.perf_counter()
    last_err: Exception | None = None
    data: dict[str, Any] | None = None

    with httpx.Client(timeout=timeout_s) as client:
        for attempt in range(max_retries + 1):
            try:
                resp = client.post(
                    f"{base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            except httpx.TimeoutException as exc:
                last_err = RuntimeError("nvidia_nim_timeout")
                logger.warning("NIM timeout attempt=%s", attempt + 1)
                if attempt < max_retries:
                    time.sleep(0.4 * (2**attempt))
                    continue
                _record_failure()
                raise last_err from exc
            except httpx.HTTPError as exc:
                last_err = RuntimeError(f"nvidia_nim_transport_{type(exc).__name__}")
                logger.warning("NIM transport error attempt=%s: %s", attempt + 1, exc)
                if attempt < max_retries:
                    time.sleep(0.4 * (2**attempt))
                    continue
                _record_failure()
                raise last_err from exc

            if resp.status_code in _RETRYABLE and attempt < max_retries:
                logger.warning(
                    "NIM retryable status=%s attempt=%s body=%s",
                    resp.status_code,
                    attempt + 1,
                    resp.text[:200],
                )
                time.sleep(0.5 * (2**attempt))
                continue

            if resp.status_code >= 400:
                logger.warning(
                    "NIM chat failed status=%s body=%s",
                    resp.status_code,
                    resp.text[:300],
                )
                _record_failure()
                raise RuntimeError(f"nvidia_nim_http_{resp.status_code}")

            data = resp.json()
            break

    if data is None:
        _record_failure()
        raise last_err or RuntimeError("nvidia_nim_empty")

    latency_ms = int((time.perf_counter() - started) * 1000)
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    usage = data.get("usage") or {}
    _record_success()
    return {
        "content": str(message.get("content") or "").strip(),
        "model": str(data.get("model") or use_model),
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
        "latency_ms": latency_ms,
        "raw_id": data.get("id"),
    }
