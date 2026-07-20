"""Basic tests for scanner / memory / writer."""

import json
from pathlib import Path

from repomind.memory import diff_snapshots, load_latest_snapshots, save_snapshot
from repomind.scanner import scan_project
from repomind.writer import render_agents_md, update_project_memory


def make_py_project(tmp_path: Path) -> Path:
    root = tmp_path / "pyproj"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1"\n', encoding="utf-8"
    )
    (root / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    return root


def test_scan_python_project(tmp_path):
    root = make_py_project(tmp_path)
    facts = scan_project(root)
    assert facts.name == "pyproj"
    assert any("Python" in s for s in facts.stacks)
    assert facts.languages.get("Python") == 1
    assert facts.file_count == 3
    assert "Demo" in facts.readme_excerpt


def test_snapshot_and_diff(tmp_path):
    root = make_py_project(tmp_path)
    facts1 = scan_project(root).to_dict()
    save_snapshot(root, facts1)
    (root / "extra.py").write_text("x = 1\n", encoding="utf-8")
    facts2 = scan_project(root).to_dict()
    save_snapshot(root, facts2)
    snaps = load_latest_snapshots(root, n=2)
    assert len(snaps) == 2
    diff = diff_snapshots(snaps[1], snaps[0])
    assert "file_count" in diff
    assert diff["file_count"]["after"] == diff["file_count"]["before"] + 1


def test_render_agents_md(tmp_path):
    root = make_py_project(tmp_path)
    facts = scan_project(root).to_dict()
    md = render_agents_md(facts)
    assert "# AGENTS.md" in md
    assert "pyproj" in md
    assert "Python" in md


def test_update_project_memory(tmp_path):
    root = make_py_project(tmp_path)
    p1 = update_project_memory(root, None)
    assert p1.exists()
    p2 = update_project_memory(root, {"file_count": {"before": 3, "after": 4}})
    text = p2.read_text(encoding="utf-8")
    assert text.count("## ") >= 2
    assert "file_count" in text