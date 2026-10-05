"""Anthropic API provider (official SDK)."""
from __future__ import annotations

import os

from .base import LLMError, LLMProvider


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def _key(self) -> str | None:
        return os.environ.get(self.cfg.get("api_key_env") or "ANTHROPIC_API_KEY")

    def available(self) -> bool:
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return bool(self._key() or os.environ.get("ANTHROPIC_AUTH_TOKEN"))

    def complete(self, system: str, prompt: str, *, max_tokens: int = 8000) -> str:
        import anthropic

        client = anthropic.Anthropic()  # resolves credentials from the environment
        max_tokens = max(max_tokens, int(self.cfg.get("max_tokens", 16000)))
        try:
            # Stream so large outputs never hit HTTP timeouts.
            with client.messages.stream(
                model=self.cfg.get("model", "claude-opus-5-5"),
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                msg = stream.get_final_message()
        except anthropic.RateLimitError as e:
            raise LLMError(f"anthropic rate limited: {e}") from e
        except anthropic.AuthenticationError as e:
            raise LLMError(f"anthropic auth failed: {e}") from e
        except anthropic.APIStatusError as e:
            raise LLMError(f"anthropic API error {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise LLMError(f"anthropic connection error: {e}") from e
        if msg.stop_reason == "refusal":
            raise LLMError("anthropic declined the request")
        text = "".join(b.text for b in msg.content if b.type == "text")
        if not text.strip():
            raise LLMError("anthropic returned no text")
        return text
