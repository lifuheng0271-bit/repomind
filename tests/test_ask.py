"""Tests for llm config loading and ask context building (no real LLM needed)."""

from pathlib import Path

import pytest

from repomind.ask import ask_question, build_context
from repomind.llm import LLMConfig, LLMNotConfigured, load_llm_config


def make_project(tmp_path: Path, llm_enabled: bool = True) -> Path:
    root = tmp_path / "proj"
    (root / ".repomind").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1"\n', encoding="utf-8"
    )
    (root / "README.md").write_text("# Demo project\nRun with `python main.py`.\n", encoding="utf-8")
    cfg = f"""\
[llm]
enabled = {"true" if llm_enabled else "false"}
endpoint = "http://localhost:11434/v1"
model = "test-model"
"""
    (root / ".repomind" / "config.toml").write_text(cfg, encoding="utf-8")
    return root


def test_load_llm_config_ok(tmp_path):
    root = make_project(tmp_path)
    cfg = load_llm_config(root)
    assert cfg.model == "test-model"
    assert cfg.chat_url == "http://localhost:11434/v1/chat/completions"


def test_load_llm_config_disabled(tmp_path):
    root = make_project(tmp_path, llm_enabled=False)
    with pytest.raises(LLMNotConfigured):
        load_llm_config(root)


def test_load_llm_config_missing(tmp_path):
    with pytest.raises(LLMNotConfigured):
        load_llm_config(tmp_path)  # no .repomind at all


def test_chat_url_no_double_suffix():
    cfg = LLMConfig(endpoint="http://x/v1/chat/completions", model="m")
    assert cfg.chat_url == "http://x/v1/chat/completions"


def test_build_context_includes_facts_and_readme(tmp_path):
    root = make_project(tmp_path)
    ctx = build_context(root)
    assert "Project facts (JSON)" in ctx
    assert "demo" in ctx or "proj" in ctx
    assert "README excerpt" in ctx
    assert "pyproject.toml" in ctx


def test_ask_question_uses_chat(tmp_path, monkeypatch):
    root = make_project(tmp_path)
    captured = {}

    def fake_chat(config, system, user):
        captured["system"] = system
        captured["user"] = user
        return "the answer"

    monkeypatch.setattr("repomind.ask.chat", fake_chat)
    cfg = LLMConfig(endpoint="http://localhost/v1", model="m")
    out = ask_question(root, "How do I run this?", cfg)
    assert out == "the answer"
    assert "How do I run this?" in captured["user"]
    assert "RepoMind" in captured["system"]