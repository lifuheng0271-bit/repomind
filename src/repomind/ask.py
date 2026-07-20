"""ask: answer questions about the project using facts + optional file peeking."""

from __future__ import annotations

import json
from pathlib import Path

from .llm import LLMConfig, chat
from .memory import load_latest_snapshots
from .scanner import scan_project

SYSTEM_PROMPT = """\
You are RepoMind, a project-knowledge assistant running locally.
Answer the user's question about THIS project only, based on the provided
project facts (JSON) and file excerpts. Be concise and practical.
If the facts are insufficient, say what is missing instead of guessing.
Answer in the same language as the user's question.
"""

# Files worth including as extra context if they exist (small ones only).
CONTEXT_FILES = (
    "AGENTS.md",
    "PROJECT_MEMORY.md",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "Makefile",
)

MAX_FILE_CHARS = 2000
MAX_README_CHARS = 3000


def build_context(root: str | Path) -> str:
    """Assemble facts + key file excerpts into a single context string."""
    root = Path(root)
    snaps = load_latest_snapshots(root, n=1)
    facts = snaps[0] if snaps else scan_project(root).to_dict()

    parts: list[str] = []
    slim = {k: v for k, v in facts.items() if k != "readme_excerpt"}
    parts.append("## Project facts (JSON)\n" + json.dumps(slim, ensure_ascii=False, indent=1))

    readme = facts.get("readme_excerpt") or ""
    if readme:
        parts.append("## README excerpt\n" + readme[:MAX_README_CHARS])

    for name in CONTEXT_FILES:
        p = root / name
        if p.exists() and p.is_file():
            try:
                text = p.read_text(encoding="utf-8", errors="replace")[:MAX_FILE_CHARS]
                parts.append(f"## {name}\n{text}")
            except Exception:
                continue

    return "\n\n".join(parts)


def ask_question(root: str | Path, question: str, config: LLMConfig) -> str:
    context = build_context(root)
    user = f"{context}\n\n---\n\n## Question\n{question}"
    return chat(config, SYSTEM_PROMPT, user)