"""doctor: diagnose config, environment, and LLM connectivity."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from .llm import LLMNotConfigured, LLMRequestError, chat, load_llm_config


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    warn: bool = False  # ok=True + warn=True -> yellow notice


def check_python() -> CheckResult:
    v = sys.version_info
    ok = (v.major, v.minor) >= (3, 10)
    return CheckResult(
        "Python >= 3.10",
        ok,
        f"found {v.major}.{v.minor}.{v.micro}",
    )


def check_git() -> CheckResult:
    path = shutil.which("git")
    if path:
        return CheckResult("git available", True, path)
    return CheckResult(
        "git available", True, "not found — git info will be skipped", warn=True
    )


def check_initialized(root: Path) -> CheckResult:
    cfg = root / ".repomind" / "config.toml"
    if cfg.exists():
        return CheckResult("repomind initialized", True, str(cfg))
    return CheckResult(
        "repomind initialized", False, "run `repomind init` first"
    )


def check_snapshots(root: Path) -> CheckResult:
    sdir = root / ".repomind" / "snapshots"
    if not sdir.exists():
        return CheckResult("snapshots", True, "no snapshots yet — run `repomind scan`", warn=True)
    count = len(list(sdir.glob("scan-*.json")))
    if count == 0:
        return CheckResult("snapshots", True, "no snapshots yet — run `repomind scan`", warn=True)
    return CheckResult("snapshots", True, f"{count} snapshot(s)")


def check_docs(root: Path) -> CheckResult:
    agents = root / "AGENTS.md"
    if agents.exists():
        return CheckResult("AGENTS.md", True, "present")
    return CheckResult("AGENTS.md", True, "missing — run `repomind update`", warn=True)


def check_llm_config(root: Path) -> tuple[CheckResult, object]:
    try:
        cfg = load_llm_config(root)
    except LLMNotConfigured as e:
        first_line = str(e).splitlines()[0]
        return CheckResult("LLM config", True, f"disabled/not set: {first_line}", warn=True), None
    detail = f"format={cfg.api_format}, model={cfg.model}, endpoint={cfg.endpoint}"
    if cfg.api_key:
        detail += ", api_key=***set***"
    return CheckResult("LLM config", True, detail), cfg


def check_llm_connectivity(cfg) -> CheckResult:
    try:
        reply = chat(cfg, "You are a health check.", "Reply with exactly: OK")
    except LLMRequestError as e:
        return CheckResult("LLM connectivity", False, str(e))
    snippet = reply[:60].replace("\n", " ")
    return CheckResult("LLM connectivity", True, f"reachable, reply: {snippet!r}")


def run_doctor(root: str | Path, skip_llm_ping: bool = False) -> list[CheckResult]:
    root = Path(root)
    results: list[CheckResult] = [
        check_python(),
        check_git(),
        check_initialized(root),
        check_snapshots(root),
        check_docs(root),
    ]
    llm_result, cfg = check_llm_config(root)
    results.append(llm_result)
    if cfg is not None and not skip_llm_ping:
        results.append(check_llm_connectivity(cfg))
    return results