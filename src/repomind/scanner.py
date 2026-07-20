"""Project scanner: produce ProjectFacts without any LLM."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path

DEFAULT_IGNORES = {
    ".git", ".repomind", "node_modules", ".venv", "venv", "__pycache__",
    "target", "dist", "build", ".cache", ".idea", ".vscode", ".mypy_cache",
    ".pytest_cache", ".tox", "coverage", ".next", ".nuxt",
}

LANG_BY_EXT = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".jsx": "JavaScript", ".rs": "Rust", ".go": "Go", ".java": "Java",
    ".kt": "Kotlin", ".c": "C", ".cpp": "C++", ".h": "C/C++ header",
    ".sh": "Shell", ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
    ".md": "Markdown", ".toml": "TOML", ".yaml": "YAML", ".yml": "YAML",
    ".json": "JSON", ".html": "HTML", ".css": "CSS", ".sql": "SQL",
}


@dataclass
class ProjectFacts:
    root: str
    name: str
    stacks: list[str] = field(default_factory=list)
    languages: dict[str, int] = field(default_factory=dict)
    file_count: int = 0
    total_size_bytes: int = 0
    entry_points: list[str] = field(default_factory=list)
    commands: dict[str, str] = field(default_factory=dict)
    readme_excerpt: str = ""
    git_branch: str = ""
    git_last_commit: str = ""
    top_level: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _detect_python(root: Path, facts: ProjectFacts) -> None:
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        facts.stacks.append("Python (pyproject)")
        try:
            import tomllib
            data = tomllib.loads(pyproject.read_text(encoding="utf-8", errors="replace"))
            scripts = data.get("project", {}).get("scripts", {})
            for name in scripts:
                facts.entry_points.append(f"console script: {name}")
            facts.commands.setdefault("install", "pip install -e .")
            facts.commands.setdefault("test", "pytest")
        except Exception:
            pass
    elif (root / "requirements.txt").exists():
        facts.stacks.append("Python (requirements.txt)")
        facts.commands.setdefault("install", "pip install -r requirements.txt")


def _detect_node(root: Path, facts: ProjectFacts) -> None:
    pkg = root / "package.json"
    if not pkg.exists():
        return
    facts.stacks.append("Node.js")
    try:
        data = json.loads(pkg.read_text(encoding="utf-8", errors="replace"))
        for script_name, script_cmd in (data.get("scripts") or {}).items():
            facts.commands[f"npm run {script_name}"] = str(script_cmd)
        if data.get("main"):
            facts.entry_points.append(f"main: {data['main']}")
        facts.commands.setdefault("install", "npm install")
    except Exception:
        pass


def _detect_rust(root: Path, facts: ProjectFacts) -> None:
    if (root / "Cargo.toml").exists():
        facts.stacks.append("Rust")
        facts.commands.setdefault("build", "cargo build")
        facts.commands.setdefault("test", "cargo test")
        facts.commands.setdefault("run", "cargo run")


def _detect_go(root: Path, facts: ProjectFacts) -> None:
    if (root / "go.mod").exists():
        facts.stacks.append("Go")
        facts.commands.setdefault("build", "go build ./...")
        facts.commands.setdefault("test", "go test ./...")


def _read_readme(root: Path, max_chars: int = 1500) -> str:
    for name in ("README.md", "README.rst", "README.txt", "README"):
        p = root / name
        if p.exists():
            try:
                return p.read_text(encoding="utf-8", errors="replace")[:max_chars]
            except Exception:
                return ""
    return ""


def _git_info(root: Path, facts: ProjectFacts) -> None:
    def _run(args: list[str]) -> str:
        try:
            out = subprocess.run(
                args, cwd=root, capture_output=True, text=True, timeout=10
            )
            return out.stdout.strip() if out.returncode == 0 else ""
        except Exception:
            return ""

    facts.git_branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    facts.git_last_commit = _run(["git", "log", "-1", "--format=%h %s (%ci)"])


def scan_project(root: str | Path, ignores: set[str] | None = None) -> ProjectFacts:
    """Walk the project tree and return structured ProjectFacts."""
    root = Path(root).resolve()
    ignores = (ignores or set()) | DEFAULT_IGNORES
    facts = ProjectFacts(root=str(root), name=root.name)

    for child in sorted(root.iterdir()):
        if child.name not in ignores and not child.name.startswith("."):
            facts.top_level.append(child.name + ("/" if child.is_dir() else ""))

    for path in root.rglob("*"):
        parts = set(path.relative_to(root).parts)
        if parts & ignores:
            continue
        if path.is_file():
            facts.file_count += 1
            try:
                facts.total_size_bytes += path.stat().st_size
            except OSError:
                pass
            lang = LANG_BY_EXT.get(path.suffix.lower())
            if lang:
                facts.languages[lang] = facts.languages.get(lang, 0) + 1

    _detect_python(root, facts)
    _detect_node(root, facts)
    _detect_rust(root, facts)
    _detect_go(root, facts)
    facts.readme_excerpt = _read_readme(root)
    _git_info(root, facts)
    return facts