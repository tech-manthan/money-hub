"""Per-task provider chains with automatic fallback."""
from __future__ import annotations

import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from ..config import Config, get_config
from .anthropic_api import AnthropicProvider
from .base import LLMError, LLMProvider, extract_json
from .claude_cli import ClaudeCLIProvider
from .openai_compat import OpenAICompatProvider

log = logging.getLogger("moneyhub.llm")
T = TypeVar("T", bound=BaseModel)

JSON_RULES = (
    "Reply with a single JSON value that matches the requested schema exactly. "
    "No markdown fences, no commentary, no trailing text."
)


class LLMRouter:
    def __init__(self, cfg: Config | None = None):
        self.cfg = cfg or get_config()
        self._providers: dict[str, LLMProvider] = {}
        self.last_used: str | None = None

    def provider(self, name: str) -> LLMProvider | None:
        if name in self._providers:
            return self._providers[name]
        pcfg = self.cfg.get(f"llm.providers.{name}", {}) or {}
        p: LLMProvider | None
        if name == "claude_cli":
            p = ClaudeCLIProvider(pcfg)
        elif name == "anthropic":
            p = AnthropicProvider(pcfg)
        elif name == "builtin":
            p = None  # handled by callers: they supply an offline fallback
        else:
            p = OpenAICompatProvider(name, pcfg) if pcfg.get("base_url") else None
        if p:
            self._providers[name] = p
        return p

    def chain(self, task: str, override: list[str] | None = None) -> list[str]:
        return override or self.cfg.get(f"llm.tasks.{task}") or ["builtin"]

    def status(self) -> list[dict]:
        names = {n for t in (self.cfg.get("llm.tasks") or {}).values() for n in t}
        rows = []
        for n in sorted(names):
            if n == "builtin":
                rows.append({"name": n, "available": True, "model": "offline library"})
                continue
            p = self.provider(n)
            rows.append({"name": n, "available": bool(p and p.available()), "model": p.describe() if p else "-"})
        return rows

    def complete_json(self, task: str, system: str, prompt: str, model: type[T], *,
                      providers: list[str] | None = None, max_tokens: int = 8000) -> T | None:
        """Try each provider in the task chain; return a validated model or None if only `builtin` is left."""
        schema_hint = f"\n\nJSON schema:\n{model.model_json_schema()}"
        errors: list[str] = []
        for name in self.chain(task, providers):
            if name == "builtin":
                break
            p = self.provider(name)
            if not p or not p.available():
                continue
            for attempt in range(2):
                try:
                    raw = p.complete(system + "\n" + JSON_RULES, prompt + schema_hint, max_tokens=max_tokens)
                    obj = model.model_validate(extract_json(raw))
                    self.last_used = f"{name}:{p.describe()}"
                    return obj
                except (LLMError, ValidationError, ValueError) as e:
                    errors.append(f"{name}: {str(e)[:200]}")
                    log.warning("provider %s attempt %d failed: %s", name, attempt + 1, str(e)[:200])
                    if isinstance(e, LLMError) and "rate" in str(e).lower():
                        break
        self.last_used = "builtin"
        if errors:
            log.warning("all providers failed, using builtin: %s", "; ".join(errors))
        return None


_router: LLMRouter | None = None


def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
