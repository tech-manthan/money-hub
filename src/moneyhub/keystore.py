"""API keys and tokens, kept in a git-ignored `.env` file in the MoneyHub folder (owner-readable only) and loaded into the
environment. The UI can add, test and remove them; values are never logged or shown in full."""
from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .paths import REPO_ROOT


@dataclass(frozen=True)
class KeyDef:
    env: str
    label: str
    group: str            # "writing" | "art"
    provider: str         # provider name used elsewhere in MoneyHub
    url: str = ""         # where to get one
    secret: bool = True   # False for plain settings such as a local URL
    note: str = ""


KEYS: list[KeyDef] = [
    KeyDef("ANTHROPIC_API_KEY", "Anthropic API key", "writing", "anthropic", "https://console.anthropic.com/settings/keys", note="Pay per use."),
    KeyDef("GEMINI_API_KEY", "Google Gemini API key", "writing", "gemini", "https://aistudio.google.com/apikey", note="Has a free tier."),
    KeyDef("GROQ_API_KEY", "Groq API key", "writing", "groq", "https://console.groq.com/keys", note="Has a free tier."),
    KeyDef("OPENROUTER_API_KEY", "OpenRouter API key", "writing", "openrouter", "https://openrouter.ai/keys", note="Some models are free."),
    KeyDef("HF_TOKEN", "Hugging Face token", "art", "huggingface", "https://huggingface.co/settings/tokens", note="FLUX image model."),
    KeyDef("TOGETHER_API_KEY", "Together AI key", "art", "together", "https://api.together.ai/settings/api-keys"),
    KeyDef("OPENAI_API_KEY", "OpenAI API key", "art", "openai", "https://platform.openai.com/api-keys"),
    KeyDef("MONEYHUB_ART_URL", "Local image server URL", "art", "local_http", secret=False, note="e.g. http://localhost:8188/generate"),
]
BY_ENV = {k.env: k for k in KEYS}
_LINE = re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$")
_from_file: set[str] = set()


def env_path() -> Path:
    return Path(os.environ.get("MONEYHUB_HOME") or REPO_ROOT) / ".env"


def _read() -> dict[str, str]:
    p = env_path()
    out: dict[str, str] = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            m = _LINE.match(line)
            if m:
                v = m.group(2)
                out[m.group(1)] = v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'" else v
    return out


def load_env() -> None:
    """Put saved keys into the environment. A variable already set in your shell wins."""
    for k, v in _read().items():
        if k in BY_ENV and v and k not in os.environ:
            os.environ[k] = v
            _from_file.add(k)


def mask(value: str, secret: bool = True) -> str:
    if not secret:
        return value
    return "•" * 8 + value[-4:] if len(value) >= 12 else "•" * 8


def status() -> list[dict]:
    saved = _read()
    rows = []
    for k in KEYS:
        v = os.environ.get(k.env, "")
        rows.append({"env": k.env, "label": k.label, "group": k.group, "provider": k.provider, "url": k.url, "note": k.note,
                     "set": bool(v), "masked": mask(v, k.secret) if v else "", "secret": k.secret,
                     "source": "" if not v else (".env file" if k.env in saved and (k.env in _from_file or saved[k.env] == v) else "your shell environment")})
    return rows


def _write(values: dict[str, str]) -> None:
    p = env_path()
    lines = [f"{k}={v}" for k, v in values.items()]
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".env.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("# MoneyHub keys. Written by the Settings page. Never commit or share this file.\n" + "\n".join(lines) + "\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def save(name: str, value: str) -> None:
    if name not in BY_ENV:
        raise ValueError("unknown setting")
    value = value.strip()
    if not value or len(value) > 500 or re.search(r"[\r\n\x00]", value):
        raise ValueError("that value is empty, too long, or has line breaks")
    if not BY_ENV[name].secret and not re.match(r"^https?://", value):
        raise ValueError("the URL must start with http:// or https://")
    values = _read()
    values[name] = value
    _write(values)
    os.environ[name] = value
    _from_file.add(name)


def remove(name: str) -> None:
    if name not in BY_ENV:
        raise ValueError("unknown setting")
    values = _read()
    if name in values:
        values.pop(name)
        _write(values)
    if name in _from_file:
        os.environ.pop(name, None)
        _from_file.discard(name)


def scrub(text: str) -> str:
    """Remove any saved secret from a message before it is shown."""
    for k in KEYS:
        v = os.environ.get(k.env, "")
        if k.secret and v and v in text:
            text = text.replace(v, "***")
    return text
