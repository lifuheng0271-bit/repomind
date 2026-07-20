"""Tests for doctor checks (no real LLM needed)."""

from pathlib import Path

from repomind.doctor import (
    check_docs,
    check_initialized,
    check_llm_config,
    check_llm_connectivity,
    check_python,
    check_snapshots,
    run_doctor,
)
from repomind.llm import LLMConfig


def make_project(tmp_path: Path, llm: bool = False) -> Path:
    root = tmp_path / "proj"
    (root / ".repomind" / "snapshots").mkdir(parents=True)
    cfg = "[llm]\nenabled = false\n"
    if llm:
        cfg = '[llm]\nenabled = true\nendpoint = "http://x/v1"\nmodel = "m"\n'
    (root / ".repomind" / "config.toml").write_text(cfg, encoding="utf-8")
    return root


def test_check_python_ok():
    r = check_python()
    assert r.ok  # we run tests on >= 3.10


def test_check_initialized(tmp_path):
    root = make_project(tmp_path)
    assert check_initialized(root).ok
    assert not check_initialized(tmp_path / "nowhere").ok


def test_check_snapshots_warns_when_empty(tmp_path):
    root = make_project(tmp_path)
    r = check_snapshots(root)
    assert r.ok and r.warn
    (root / ".repomind" / "snapshots" / "scan-1.json").write_text("{}", encoding="utf-8")
    r2 = check_snapshots(root)
    assert r2.ok and not r2.warn


def test_check_docs(tmp_path):
    root = make_project(tmp_path)
    assert check_docs(root).warn
    (root / "AGENTS.md").write_text("# AGENTS.md\n", encoding="utf-8")
    assert not check_docs(root).warn


def test_check_llm_config_disabled_is_warn(tmp_path):
    root = make_project(tmp_path, llm=False)
    r, cfg = check_llm_config(root)
    assert r.ok and r.warn
    assert cfg is None


def test_check_llm_config_enabled(tmp_path):
    root = make_project(tmp_path, llm=True)
    r, cfg = check_llm_config(root)
    assert r.ok and not r.warn
    assert cfg is not None
    assert "format=chat" in r.detail


def test_check_llm_connectivity_mock(monkeypatch):
    import repomind.doctor as doc

    monkeypatch.setattr(doc, "chat", lambda cfg, s, u: "OK")
    r = check_llm_connectivity(LLMConfig(endpoint="http://x/v1", model="m"))
    assert r.ok

    from repomind.llm import LLMRequestError

    def boom(cfg, s, u):
        raise LLMRequestError("down")

    monkeypatch.setattr(doc, "chat", boom)
    r2 = check_llm_connectivity(LLMConfig(endpoint="http://x/v1", model="m"))
    assert not r2.ok


def test_run_doctor_skip_ping(tmp_path):
    root = make_project(tmp_path, llm=True)
    results = run_doctor(root, skip_llm_ping=True)
    names = [r.name for r in results]
    assert "LLM config" in names
    assert "LLM connectivity" not in names  # skipped
    assert all(r.ok for r in results)