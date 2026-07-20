"""Tests for TUI helpers and app composition (textual Pilot, headless)."""

import json
from pathlib import Path

import pytest

pytest.importorskip("textual")

from repomind.tui import RepoMindApp, _doctor_md, _facts, _overview_md


def make_project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / ".repomind" / "snapshots").mkdir(parents=True)
    (root / ".repomind" / "config.toml").write_text("[llm]\nenabled = false\n", encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname = "demo"\nversion = "0.1"\n', encoding="utf-8")
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    snap = {
        "root": str(root), "name": "proj", "stacks": ["Python (pyproject)"],
        "languages": {"Python": 2}, "file_count": 2, "total_size_bytes": 100,
        "entry_points": [], "commands": {"test": "pytest"}, "readme_excerpt": "# Demo",
        "git_branch": "main", "git_last_commit": "abc init", "top_level": ["README.md"],
    }
    (root / ".repomind" / "snapshots" / "scan-20260720-000000.json").write_text(
        json.dumps(snap), encoding="utf-8"
    )
    return root


def test_overview_md(tmp_path):
    root = make_project(tmp_path)
    md = _overview_md(_facts(root))
    assert "# proj" in md
    assert "Python (pyproject)" in md
    assert "pytest" in md


def test_doctor_md(tmp_path):
    root = make_project(tmp_path)
    md = _doctor_md(root)
    assert "# Doctor" in md
    assert "repomind initialized" in md


@pytest.mark.asyncio
async def test_app_mounts_and_shows_tabs(tmp_path):
    root = make_project(tmp_path)
    app = RepoMindApp(root)
    async with app.run_test() as pilot:
        await pilot.pause()
        from textual.widgets import TabbedContent

        tc = app.query_one(TabbedContent)
        panes = [p.id for p in tc.query("TabPane")]
        assert "tab-overview" in panes
        assert "tab-snapshots" in panes
        assert "tab-doctor" in panes
        assert "tab-chat" in panes


@pytest.mark.asyncio
async def test_chat_without_llm_replies_notice(tmp_path):
    root = make_project(tmp_path)
    app = RepoMindApp(root)
    async with app.run_test() as pilot:
        await pilot.pause()
        from textual.widgets import Input

        chat_input = app.query_one("#chat-input", Input)
        chat_input.value = "怎么运行？"
        chat_input.focus()
        await pilot.press("enter")
        # wait for worker to finish
        for _ in range(50):
            await pilot.pause(0.1)
            if app._chat_history and "思考中" not in app._chat_history[-1]:
                break
        assert any("LLM 未启用" in m for m in app._chat_history)