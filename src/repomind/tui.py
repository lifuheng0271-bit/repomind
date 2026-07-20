"""RepoMind TUI: interactive terminal UI built on textual."""

from __future__ import annotations

import json
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Footer,
    Header,
    Input,
    ListItem,
    ListView,
    Markdown,
    Static,
    TabbedContent,
    TabPane,
)
from textual.worker import Worker, WorkerState

from .memory import diff_snapshots, load_latest_snapshots, snapshots_dir
from .scanner import scan_project


# ---------- helpers ----------

def _facts(root: Path) -> dict:
    snaps = load_latest_snapshots(root, n=1)
    return snaps[0] if snaps else scan_project(root).to_dict()


def _overview_md(facts: dict) -> str:
    langs = facts.get("languages", {}) or {}
    lang_lines = "\n".join(
        f"- {k}: {v} files" for k, v in sorted(langs.items(), key=lambda x: -x[1])
    ) or "- (none)"
    cmds = facts.get("commands", {}) or {}
    cmd_lines = "\n".join(f"- `{k}` → `{v}`" for k, v in cmds.items()) or "- (none)"
    top = "\n".join(f"- {t}" for t in facts.get("top_level", [])) or "- (none)"
    return f"""\
# {facts.get('name', '?')}

**Stacks:** {', '.join(facts.get('stacks') or ['unknown'])}
**Files:** {facts.get('file_count', 0)} · **Git:** `{facts.get('git_branch') or '-'}` — {facts.get('git_last_commit') or '-'}

## Top level
{top}

## Languages
{lang_lines}

## Commands
{cmd_lines}
"""


def _doctor_md(root: Path) -> str:
    from .doctor import run_doctor

    lines = ["# Doctor\n"]
    failed = 0
    for r in run_doctor(root, skip_llm_ping=True):
        mark = "✅" if (r.ok and not r.warn) else ("⚠️" if r.ok else "❌")
        if not r.ok:
            failed += 1
        lines.append(f"- {mark} **{r.name}** — {r.detail}")
    lines.append(
        "\n> LLM 在线连通性未测试（TUI 内默认跳过）；需要时运行 `repomind doctor`。"
    )
    lines.append(
        f"\n**{failed} check(s) failed.**" if failed else "\n**All checks passed.**"
    )
    return "\n".join(lines)


# ---------- app ----------

class RepoMindApp(App):
    """RepoMind interactive TUI."""

    TITLE = "RepoMind"
    CSS = """
    #chat-log { height: 1fr; border: round $primary; padding: 0 1; }
    #chat-input { dock: bottom; }
    #snap-list { width: 34; border: round $primary; }
    #snap-detail { border: round $secondary; padding: 0 1; }
    .pane-body { padding: 1 2; }
    """
    BINDINGS = [
        Binding("q", "quit", "退出"),
        Binding("r", "refresh", "重新扫描"),
    ]

    def __init__(self, root: str | Path = ".") -> None:
        super().__init__()
        self.root = Path(root).resolve()
        self.sub_title = str(self.root)
        self._chat_history: list[str] = []

    # ----- layout -----

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="tab-overview"):
            with TabPane("概览", id="tab-overview"):
                with VerticalScroll(classes="pane-body"):
                    yield Markdown(id="overview-md")
            with TabPane("快照", id="tab-snapshots"):
                with Horizontal(classes="pane-body"):
                    yield ListView(id="snap-list")
                    with VerticalScroll(id="snap-detail"):
                        yield Markdown(id="snap-md")
            with TabPane("Doctor", id="tab-doctor"):
                with VerticalScroll(classes="pane-body"):
                    yield Markdown(id="doctor-md")
            with TabPane("Chat", id="tab-chat"):
                with Vertical(classes="pane-body"):
                    with VerticalScroll(id="chat-log"):
                        yield Markdown(id="chat-md")
                    yield Input(
                        placeholder="问点关于这个项目的问题…（回车发送，需启用 LLM）",
                        id="chat-input",
                    )
        yield Footer()

    # ----- lifecycle -----

    def on_mount(self) -> None:
        self.action_refresh()

    def action_refresh(self) -> None:
        facts = _facts(self.root)
        self.query_one("#overview-md", Markdown).update(_overview_md(facts))
        self.query_one("#doctor-md", Markdown).update(_doctor_md(self.root))
        self._load_snapshot_list()

    # ----- snapshots tab -----

    def _load_snapshot_list(self) -> None:
        lv = self.query_one("#snap-list", ListView)
        lv.clear()
        sdir = snapshots_dir(self.root)
        self._snap_files = (
            sorted(sdir.glob("scan-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if sdir.exists()
            else []
        )
        for f in self._snap_files:
            lv.append(ListItem(Static(f.stem.replace("scan-", ""))))
        if not self._snap_files:
            self.query_one("#snap-md", Markdown).update(
                "*没有快照。先运行 `repomind scan`，或按 `r` 重新扫描。*"
            )

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id != "snap-list" or event.list_view.index is None:
            return
        idx = event.list_view.index
        if not (0 <= idx < len(self._snap_files)):
            return
        try:
            curr = json.loads(self._snap_files[idx].read_text(encoding="utf-8"))
        except Exception:
            return
        md = [f"# 快照 {self._snap_files[idx].stem}\n"]
        md.append(f"- files: {curr.get('file_count')}")
        md.append(f"- stacks: {', '.join(curr.get('stacks') or [])}")
        md.append(f"- git: {curr.get('git_last_commit') or '-'}")
        if idx + 1 < len(self._snap_files):
            try:
                prev = json.loads(self._snap_files[idx + 1].read_text(encoding="utf-8"))
                diff = diff_snapshots(prev, curr)
                md.append("\n## 相比上一个快照")
                if diff:
                    for k, v in diff.items():
                        md.append(f"- **{k}**: `{v}`")
                else:
                    md.append("- 无结构性变化")
            except Exception:
                pass
        self.query_one("#snap-md", Markdown).update("\n".join(md))

    # ----- chat tab -----

    def _render_chat(self) -> None:
        self.query_one("#chat-md", Markdown).update(
            "\n\n".join(self._chat_history) or "*还没有对话。*"
        )
        self.query_one("#chat-log", VerticalScroll).scroll_end(animate=False)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "chat-input":
            return
        question = event.value.strip()
        if not question:
            return
        event.input.value = ""
        self._chat_history.append(f"**你：** {question}")
        self._chat_history.append("*思考中…*")
        self._render_chat()
        self.run_worker(lambda: self._ask(question), exclusive=True, thread=True)

    def _ask(self, question: str) -> str:
        """Blocking LLM call, runs in worker thread."""
        from .ask import ask_question
        from .llm import LLMNotConfigured, LLMRequestError, load_llm_config

        try:
            cfg = load_llm_config(self.root)
            return ask_question(self.root, question, cfg)
        except LLMNotConfigured as e:
            return f"（LLM 未启用）{str(e).splitlines()[0]}"
        except LLMRequestError as e:
            return f"（请求失败）{e}"

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state is WorkerState.SUCCESS and isinstance(event.worker.result, str):
            if self._chat_history and self._chat_history[-1] == "*思考中…*":
                self._chat_history[-1] = f"**RepoMind：** {event.worker.result}"
                self._render_chat()


def run_ui(root: str | Path = ".") -> None:
    RepoMindApp(root).run()