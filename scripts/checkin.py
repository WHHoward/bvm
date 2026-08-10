#!/usr/bin/env python3
"""checkin.py -- one-screen project status reminder (2026-08-10, user request).

Run at session start (or whenever the user asks "where are we?"):
    python3 scripts/checkin.py

Reports, in order: 1) mailbox messages needing attention, 2) open task
contracts (issued/acked/delivered, awaiting audit), 3) todo status head,
4) active worktrees, 5) master working-tree cleanliness. Pure stdlib.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]


def mailbox_summary() -> list[str]:
    lines: list[str] = []
    for party in ("from-claude", "from-codex"):
        box = REPO / "research" / "mailbox" / party
        if not box.is_dir():
            continue
        messages = sorted(box.glob("*.md"))
        if not messages:
            continue
        for path in messages[-3:]:
            text = path.read_text(encoding="utf-8")
            subject = re.search(r"^subject:\s*(.+)$", text, re.M)
            sender = "codex" if party == "from-codex" else "claude"
            lines.append(f"  [{sender}] {path.stem}: {subject.group(1) if subject else '(无主题)'}")
    return lines


def _worktree_paths() -> list[Path]:
    """Linked worktree roots (the execution sandboxes)."""
    try:
        out = subprocess.run(
            ["git", "worktree", "list", "--porcelain"], capture_output=True,
            text=True, cwd=REPO, check=True,
        ).stdout
    except Exception:
        return []
    roots = [line.split(" ", 1)[1] for line in out.splitlines() if line.startswith("worktree ")]
    return [Path(root) for root in roots if Path(root) != REPO]


def open_tasks() -> list[str]:
    """Tasks with a signed request but no audit verdict yet.

    Execution artifacts may live in the task's worktree (commit: false), so
    receipts/audits are also looked up there.
    """
    lines: list[str] = []
    tasks_dir = REPO / "research" / "tasks"
    worktrees = _worktree_paths()
    if not tasks_dir.is_dir():
        return lines
    for task_dir in sorted(tasks_dir.iterdir()):
        if not task_dir.is_dir() or not (task_dir / "request.yaml").is_file():
            continue
        request = (task_dir / "request.yaml").read_text(encoding="utf-8")
        if "workflow_state: DRAFT" in request:
            continue  # not issued
        if not (task_dir / "request.sha256").is_file():
            continue
        candidates = [task_dir] + [wt / "research" / "tasks" / task_dir.name for wt in worktrees]
        receipts: list[Path] = []
        audits: list[Path] = []
        for cand in candidates:
            receipts.extend(cand.glob("attempts/*/receipt.yaml")) if (cand / "attempts").is_dir() else None
            audits.extend(cand.glob("audits/*/verdict.yaml")) if (cand / "audits").is_dir() else None
        subject = re.search(r"^subject:\s*(.+)$", request, re.M)
        objective = re.search(r"objective:\s*\"(.+?)\"", request, re.S)
        state = "ISSUED" if not receipts else ("DELIVERED(等审计)" if not audits else f"AUDITED({len(audits)})")
        lines.append(f"  {task_dir.name}: {state} — {objective.group(1)[:60] if objective else subject.group(1) if subject else ''}")
    return lines


def todo_head() -> list[str]:
    path = REPO / "memory" / "project-todo.md"
    if not path.is_file():
        return []
    lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(M\d+|Q\d+|D\d+)\s*\|\s*([^|]+?)\s*\|\s*([🟢🔴🟡⏸️🔄])\s*\|", line)
        if m:
            lines.append(f"  {m.group(1)} {m.group(2).strip()[:40]:<40} {m.group(3)}")
        if len(lines) >= 14:
            break
    return lines


def main() -> int:
    print("=" * 60)
    print("JoSIM 项目状态一览（checkin）")
    print("=" * 60)

    print("\n[1] Mailbox（对话消息）")
    msgs = mailbox_summary()
    print("\n".join(msgs) if msgs else "  （无消息）")

    print("\n[2] 任务合同（等审计）")
    tasks = open_tasks()
    print("\n".join(tasks) if tasks else "  （无已签发未审计任务）")

    print("\n[3] 任务表（todo 头部）")
    head = todo_head()
    print("\n".join(head) if head else "  （无）")

    print("\n[4] 活跃 worktree")
    try:
        out = subprocess.run(
            ["git", "worktree", "list"], capture_output=True, text=True,
            cwd=REPO, check=True,
        ).stdout.strip()
        print("  " + "\n  ".join(out.splitlines()))
    except Exception:
        print("  （无法读取）")

    print("\n[5] master 工作树")
    try:
        out = subprocess.run(
            ["git", "status", "--short"], capture_output=True, text=True,
            cwd=REPO, check=True,
        ).stdout.strip()
        print(f"  {len(out.splitlines()) if out else 0} 个未提交改动" + ("" if out else "（干净 ✅）"))
    except Exception:
        print("  （无法读取）")

    print("\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
