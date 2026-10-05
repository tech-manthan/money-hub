"""Provider-agnostic LLM interface."""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod


class LLMError(RuntimeError):
    """Raised when a provider cannot produce a usable answer."""


class LLMProvider(ABC):
    name: str = "base"

    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or {}

    @abstractmethod
    def available(self) -> bool:
        """True when the provider can plausibly be called (key/binary/server present)."""

    @abstractmethod
    def complete(self, system: str, prompt: str, *, max_tokens: int = 8000) -> str:
        """Return the raw text answer."""

    def describe(self) -> str:
        return self.cfg.get("model") or self.name


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def extract_json(text: str):
    """Parse the first JSON object/array found in an LLM answer (handles code fences and prose)."""
    text = text.strip()
    for candidate in [text] + _FENCE.findall(text):
        try:
            return json.loads(candidate.strip())
        except json.JSONDecodeError:
            pass
    start = min([i for i in (text.find("{"), text.find("[")) if i != -1], default=-1)
    if start == -1:
        raise LLMError("no JSON found in model output")
    opener = text[start]
    closer = "}" if opener == "{" else "]"
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError as e:
                    raise LLMError(f"invalid JSON from model: {e}") from e
    raise LLMError("unterminated JSON in model output")
