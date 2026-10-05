"""`claude -p` (Claude Code headless mode) provider."""
from __future__ import annotations

import shutil
import subprocess

from .base import LLMError, LLMProvider


class ClaudeCLIProvider(LLMProvider):
    name = "claude_cli"

    def _cmd(self) -> str | None:
        return shutil.which(self.cfg.get("command", "claude"))

    def available(self) -> bool:
        return self._cmd() is not None

    def complete(self, system: str, prompt: str, *, max_tokens: int = 8000) -> str:
        cmd = self._cmd()
        if not cmd:
            raise LLMError("claude CLI not found")
        args = [cmd, "-p", "--output-format", "text",
                "--disallowed-tools", "Bash,Edit,Write,Read,Glob,Grep,WebFetch,WebSearch"]
        if self.cfg.get("model"):
            args += ["--model", self.cfg["model"]]
        if system:
            args += ["--append-system-prompt", system]
        try:
            proc = subprocess.run(
                args, input=prompt, capture_output=True, text=True,
                timeout=self.cfg.get("timeout", 600),
            )
        except subprocess.TimeoutExpired as e:
            raise LLMError("claude -p timed out") from e
        if proc.returncode != 0 or not proc.stdout.strip():
            raise LLMError(f"claude -p failed ({proc.returncode}): {proc.stderr.strip()[:300]}")
        return proc.stdout
