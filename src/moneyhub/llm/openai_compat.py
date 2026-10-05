"""OpenAI-compatible chat-completions provider (Gemini, Groq, OpenRouter, Ollama, ...)."""
from __future__ import annotations

import os
import socket
from urllib.parse import urlparse

import httpx

from .base import LLMError, LLMProvider


class OpenAICompatProvider(LLMProvider):
    def __init__(self, name: str, cfg: dict | None = None):
        super().__init__(cfg)
        self.name = name

    def _key(self) -> str | None:
        env = self.cfg.get("api_key_env")
        return os.environ.get(env) if env else None

    def available(self) -> bool:
        if self.cfg.get("api_key_env"):
            return bool(self._key())
        # keyless (local) server such as Ollama: check the port answers
        u = urlparse(self.cfg.get("base_url", ""))
        try:
            with socket.create_connection((u.hostname, u.port or 80), timeout=0.4):
                return True
        except OSError:
            return False

    def complete(self, system: str, prompt: str, *, max_tokens: int = 8000) -> str:
        headers = {"Content-Type": "application/json"}
        if self._key():
            headers["Authorization"] = f"Bearer {self._key()}"
        body = {
            "model": self.cfg["model"],
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        }
        url = self.cfg["base_url"].rstrip("/") + "/chat/completions"
        try:
            r = httpx.post(url, json=body, headers=headers, timeout=self.cfg.get("timeout", 300))
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
            raise LLMError(f"{self.name} failed: {e}") from e
        if not text or not text.strip():
            raise LLMError(f"{self.name} returned no text")
        return text
