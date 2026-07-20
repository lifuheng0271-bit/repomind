"""RepoMind CLI entry point (typer)."""

from __future__ import annotations

from pathlib import Path

import typer

from . import __version__
from .memory import diff_snapshots, load_latest_snapshots, repomind_dir, save_snapshot
from .scanner import scan_project
from .writer import render_agents_md, update_project_memory, write_atomic

app = typer.Typer(help="RepoMind: repo memory & AGENTS.md maintainer for AI coding agents.")

DEFAULT_CONFIG = """\
# RepoMind config
[llm]
enabled = false
# endpoint = "http://localhost:11434/v1"   # Ollama / OpenAI-compatible
# model = "qwen3"
# api_key_env = "REPOMIND_API_KEY"

[scan]
extra_ignores = []
"""


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V", help="Show version."),
):
    if version:
        typer.echo(f"repomind {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def init(path: Path = typer.Argument(Path("."), help="Project root.")):
    """Initialize .repomind/ and config."""
    rd = repomind_dir(path)
    rd.mkdir(parents=True, exist_ok=True)
    (rd / "snapshots").mkdir(exist_ok=True)
    cfg = rd / "config.toml"
    if not cfg.exists():
        cfg.write_text(DEFAULT_CONFIG, encoding="utf-8")
        typer.echo(f"Created {cfg}")
    else:
        typer.echo(f"Already initialized: {cfg}")


@app.command()
def scan(path: Path = typer.Argument(Path("."), help="Project root.")):
    """Scan project, save snapshot, print summary."""
    facts = scan_project(path)
    snap = save_snapshot(path, facts.to_dict())
    typer.echo(f"Scanned: {facts.name}")
    typer.echo(f"  stacks:    {', '.join(facts.stacks) or 'unknown'}")
    typer.echo(f"  files:     {facts.file_count}")
    typer.echo(f"  languages: {dict(sorted(facts.languages.items(), key=lambda x: -x[1]))}")
    typer.echo(f"  snapshot:  {snap}")


@app.command()
def update(path: Path = typer.Argument(Path("."), help="Project root.")):
    """Scan then (re)generate AGENTS.md and append PROJECT_MEMORY.md entry."""
    facts = scan_project(path)
    save_snapshot(path, facts.to_dict())
    snaps = load_latest_snapshots(path, n=2)
    diff = diff_snapshots(snaps[1], snaps[0]) if len(snaps) >= 2 else None

    agents_path = Path(path) / "AGENTS.md"
    write_atomic(agents_path, render_agents_md(facts.to_dict()))
    memory_path = update_project_memory(path, diff)

    typer.echo(f"Updated {agents_path}")
    typer.echo(f"Updated {memory_path}")
    if diff:
        typer.echo(f"Changes since last scan: {list(diff.keys())}")
    else:
        typer.echo("No structural changes since last scan (or first scan).")


if __name__ == "__main__":
    app()