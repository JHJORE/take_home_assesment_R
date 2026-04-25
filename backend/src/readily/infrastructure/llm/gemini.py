"""Gemini client used by every LLM call site in Readily.

Structured output only: callers pass a Pydantic response schema and get back a
typed instance (or list of instances). We deliberately do not expose a raw
`generate(prompt) -> str` method — every call site has a well-defined output
shape, and constraining the model to it eliminates an entire class of
parse-failure bugs we used to defend against with regex fallbacks.
"""

from __future__ import annotations

import time
from typing import Any, Protocol


class GeminiClient(Protocol):
    def generate_structured(self, prompt: str, schema: Any) -> Any: ...


class GoogleGeminiClient:
    """Thin wrapper around google-genai. Constructed lazily so tests don't import it."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3-flash-preview",
        *,
        thinking_level: str | None = None,
    ) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model
        # Gemini 3 thinking levels: "minimal" | "low" | "medium" | "high". Default
        # for Gemini 3 models is "high" and can't be disabled; `None` here means
        # "don't set it explicitly, let the model default."
        self._thinking_level = thinking_level

    def generate_structured(self, prompt: str, schema: Any) -> Any:
        from google.genai import types
        from httpx import RemoteProtocolError

        # Gemini 3 docs: keep temperature at default 1.0; lowering it causes
        # looping/degraded reasoning. Do not set it here.
        config_kwargs: dict[str, Any] = {
            "response_mime_type": "application/json",
            "response_schema": schema,
        }
        if self._thinking_level is not None:
            config_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level=self._thinking_level,  # type: ignore[arg-type]
            )
        config = types.GenerateContentConfig(**config_kwargs)

        # The preview endpoint occasionally drops the connection before sending
        # headers. The SDK's built-in retry ignores RemoteProtocolError, so we
        # retry it ourselves with exponential backoff.
        delays = [0.0, 1.0, 3.0, 8.0]
        for attempt, delay in enumerate(delays):
            if delay:
                time.sleep(delay)
            try:
                resp = self._client.models.generate_content(
                    model=self._model, contents=prompt, config=config
                )
                return resp.parsed
            except RemoteProtocolError:
                if attempt == len(delays) - 1:
                    raise
