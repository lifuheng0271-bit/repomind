"""LLM client: OpenAI-compatible chat completions (works with Ollama too)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


class LLMNotConfigured(Exception):
    """Raised when [llm] is disabled or missing required fields."""


class LLMRequestError(Exception):
    """Raised when the LLM endpoint fails."""


@dataclass
class LLMConfig:
    endpoint: str
    model: str
    api_key: str = ""
    timeout: int = 120

    @property
    def chat_url(self) -> str:
        base = self.endpoint.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return base + "/chat/completions"


def load_llm_config(root: str | Path) -> LLMConfig:
    """Read [llm] section from .repomind/config.toml."""
    cfg_path = Path(root) / ".repomind" / "config.toml"
    if not cfg_path.exists():
        raise LLMNotConfigured(
            f"Config not found: {cfg_path}. Run `repomind init` first."
        )
    import tomllib

    data = tomllib.loads(cfg_path.read_text(encoding="utf-8", errors="replace"))
    llm = data.get("llm") or {}
    if not llm.get("enabled"):
        raise LLMNotConfigured(
            "LLM is disabled. Edit .repomind/config.toml:\n"
            "  [llm]\n"
            "  enabled = true\n"
            '  endpoint = "http://localhost:11434/v1"  # Ollama or any OpenAI-compatible\n'
            '  model = "qwen3"\n'
            '  api_key_env = "REPOMIND_API_KEY"  # optional'
        )
    endpoint = llm.get("endpoint", "")
    model = llm.get("model", "")
    if not endpoint or not model:
        raise LLMNotConfigured(
            "LLM enabled but `endpoint` or `model` missing in .repomind/config.toml."
        )
    api_key = ""
    key_env = llm.get("api_key_env", "")
    if key_env:
        api_key = os.environ.get(key_env, "")
    return LLMConfig(
        endpoint=endpoint,
        model=model,
        api_key=api_key,
        timeout=int(llm.get("timeout", 120)),
    )


def chat(config: LLMConfig, system: str, user: str) -> str:
    """Single-turn chat completion. Returns assistant text."""
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    req = urllib.request.Request(
        config.chat_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=config.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        raise LLMRequestError(f"HTTP {e.code} from {config.chat_url}: {detail}") from e
    except urllib.error.URLError as e:
        raise LLMRequestError(
            f"Cannot reach {config.chat_url}: {e.reason}. "
            "Is Ollama / the API server running?"
        ) from e
    try:
        return body["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as e:
        raise LLMRequestError(f"Unexpected response shape: {str(body)[:300]}") from e