"""Writer: render AGENTS.md / PROJECT_MEMORY.md from facts (template mode, no LLM)."""

from __future__ import annotations

import time
from pathlib import Path

AGENTS_TEMPLATE = """\
# AGENTS.md

> Auto-maintained by [RepoMind](https://github.com/lifuheng0271-bit/repomind). Last update: {now}

## Project

- **Name:** {name}
- **Stacks:** {stacks}
- **Files:** {file_count} ({size_mb:.1f} MB)
- **Git:** branch `{git_branch}` — {git_last_commit}

## Layout (top level)

{top_level}

## Languages

{languages}

## How to run

{commands}

## Entry points

{entry_points}

## Notes for AI agents

- Read `PROJECT_MEMORY.md` for recent changes before editing.
- Respect existing patterns; check `docs/` for specs.
"""

MEMORY_HEADER = """\
# PROJECT_MEMORY.md

> Scan history maintained by RepoMind. Newest first.
"""


def _fmt_kv(d: dict) -> str:
    if not d:
        return "- (none detected)"
    return "\n".join(f"- `{k}` → {v}" for k, v in d.items())


def _fmt_list(items: list, empty: str = "- (none)") -> str:
    if not items:
        return empty
    return "\n".join(f"- {i}" for i in items)


def render_agents_md(facts: dict) -> str:
    langs = facts.get("languages", {})
    lang_lines = "\n".join(
        f"- {lang}: {count} files"
        for lang, count in sorted(langs.items(), key=lambda x: -x[1])
    ) or "- (none detected)"
    return AGENTS_TEMPLATE.format(
        now=time.strftime("%Y-%m-%d %H:%M"),
        name=facts.get("name", "?"),
        stacks=", ".join(facts.get("stacks") or ["unknown"]),
        file_count=facts.get("file_count", 0),
        size_mb=(facts.get("total_size_bytes", 0) or 0) / 1e6,
        git_branch=facts.get("git_branch") or "-",
        git_last_commit=facts.get("git_last_commit") or "-",
        top_level=_fmt_list(facts.get("top_level") or []),
        languages=lang_lines,
        commands=_fmt_kv(facts.get("commands") or {}),
        entry_points=_fmt_list(facts.get("entry_points") or []),
    )


def render_memory_entry(diff: dict | None) -> str:
    ts = time.strftime("%Y-%m-%d %H:%M")
    if not diff:
        return f"\n## {ts}\n\n- First scan or no structural changes detected.\n"
    lines = [f"\n## {ts}\n"]
    for key, val in diff.items():
        lines.append(f"- **{key}**: `{val}`")
    return "\n".join(lines) + "\n"


def write_atomic(path: str | Path, content: str) -> None:
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def update_project_memory(root: str | Path, diff: dict | None) -> Path:
    path = Path(root) / "PROJECT_MEMORY.md"
    entry = render_memory_entry(diff)
    if path.exists():
        old = path.read_text(encoding="utf-8", errors="replace")
        body = old[len(MEMORY_HEADER):] if old.startswith(MEMORY_HEADER) else old
        write_atomic(path, MEMORY_HEADER + entry + body)
    else:
        write_atomic(path, MEMORY_HEADER + entry)
    return path