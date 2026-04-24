"""Shared test helpers.

`StubGemini` mimics the production `GeminiClient.generate_structured(prompt, schema)`
call. Each enqueued response may be a raw dict/list (validated into the declared
schema) or an already-instantiated Pydantic object (returned as-is).
"""

from __future__ import annotations

from collections import deque
from typing import Any, get_args, get_origin

from pydantic import BaseModel


class StubGemini:
    def __init__(self, *responses: Any) -> None:
        self.responses: deque[Any] = deque(responses)
        self.calls: list[tuple[str, Any]] = []

    def generate_structured(self, prompt: str, schema: Any) -> Any:
        self.calls.append((prompt, schema))
        if not self.responses:
            raise AssertionError(
                "StubGemini exhausted: more generate_structured() calls than enqueued responses"
            )
        raw = self.responses.popleft()
        return _coerce(raw, schema)


def _coerce(raw: Any, schema: Any) -> Any:
    if get_origin(schema) is list:
        (item_schema,) = get_args(schema)
        return [_coerce(item, item_schema) for item in raw]
    if isinstance(schema, type) and issubclass(schema, BaseModel):
        if isinstance(raw, schema):
            return raw
        return schema.model_validate(raw)
    return raw
