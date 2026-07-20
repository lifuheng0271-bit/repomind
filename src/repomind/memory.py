"""Snapshot memory: store scans, diff against previous snapshot."""

from __future__ import annotations

import json
import time
from pathlib import Path


def repomind_dir(root: str | Path) -> Path:
    return Path(root) / ".repomind"


def snapshots_dir(root: str | Path) -> Path:
    return repomind_dir(root) / "snapshots"


def save_snapshot(root: str | Path, facts_dict: dict) -> Path:
    sdir = snapshots_dir(root)
    sdir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    path = sdir / f"scan-{ts}.json"
    seq = 1
    while path.exists():
        path = sdir / f"scan-{ts}-{seq:02d}.json"
        seq += 1
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(facts_dict, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    return path


def load_latest_snapshots(root: str | Path, n: int = 2) -> list[dict]:
    sdir = snapshots_dir(root)
    if not sdir.exists():
        return []
    files = sorted(sdir.glob("scan-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:n]
    out = []
    for f in files:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


def diff_snapshots(prev: dict, curr: dict) -> dict:
    """Cheap structural diff between two ProjectFacts dicts."""
    changes: dict[str, object] = {}
    for key in ("file_count", "stacks", "git_branch", "git_last_commit"):
        if prev.get(key) != curr.get(key):
            changes[key] = {"before": prev.get(key), "after": curr.get(key)}
    prev_langs = prev.get("languages", {}) or {}
    curr_langs = curr.get("languages", {}) or {}
    lang_delta = {
        lang: curr_langs.get(lang, 0) - prev_langs.get(lang, 0)
        for lang in set(prev_langs) | set(curr_langs)
        if curr_langs.get(lang, 0) != prev_langs.get(lang, 0)
    }
    if lang_delta:
        changes["languages_delta"] = lang_delta
    return changes