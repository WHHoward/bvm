#!/usr/bin/env python3
"""mailbox -- async message channel between Claude Code and Codex.

The mailbox is the INFORMAL conversation channel: questions, clarifications,
status updates, reminders. Formal actions (issuing requests, ACK/receipt,
audit verdicts, stand-in records) always go through the handoff protocol
files under research/tasks/<task-id>/; mailbox messages never carry contract
authority.

Layout (MAILBOX_ROOT, defaults to <repo>/research/mailbox):
    from-claude/   messages written by Claude, read by Codex
    from-codex/    messages written by Codex, read by Claude

Each message is one markdown file named <message_id>.md:

    ---
    message_id: claude-20260809-193400
    from: claude
    to: codex
    created_at: "2026-08-09T19:34:00+08:00"
    in_reply_to: ""
    related_task: "JH-20260809-M4-001"
    subject: One-line subject
    ---
    free-form markdown body

Messages are append-only: never edit or delete a sent message; reply with a
new message using --reply-to.
"""
from __future__ import annotations

import argparse
import datetime
import os
from pathlib import Path
import re
import sys

PARTIES = ("claude", "codex", "copilot")
REQUIRED_FIELDS = ("message_id", "from", "to", "created_at", "in_reply_to",
                   "related_task", "subject")


class MailboxError(ValueError):
    """Invalid mailbox message."""


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "AGENTS.md").is_file():
            return parent
    raise MailboxError("cannot locate repository root from " + str(here))


def mailbox_root() -> Path:
    override = os.environ.get("MAILBOX_ROOT")
    if override:
        return Path(override)
    return _repo_root() / "research" / "mailbox"


def _sender_dir(root: Path, sender: str) -> Path:
    return root / f"from-{sender}"


def _timestamp() -> str:
    now = datetime.datetime.now().astimezone()
    return now.strftime("%Y%m%d-%H%M%S")


def _unique_stem(root: Path, sender: str, base: str) -> str:
    stem = f"{sender}-{base}"
    used = {p.stem for p in _sender_dir(root, sender).glob("*.md")}
    suffix = 0
    candidate = stem
    while candidate in used:
        suffix += 1
        candidate = f"{stem}-{suffix}"
    return candidate


def _write_message(root: Path, sender: str, recipient: str, subject: str,
                   body: str, reply_to: str = "", task_id: str = "") -> Path:
    if sender not in PARTIES or recipient not in PARTIES:
        raise ValueError(f"party must be one of {PARTIES}, got {sender!r}->{recipient!r}")
    if sender == recipient:
        raise ValueError("cannot message yourself")
    now = datetime.datetime.now().astimezone()
    stem = _unique_stem(root, sender, now.strftime("%Y%m%d-%H%M%S"))
    head = "\n".join(
        [
            "---",
            f"message_id: {stem}",
            f"from: {sender}",
            f"to: {recipient}",
            f'created_at: "{now.isoformat(timespec="seconds")}"',
            f"in_reply_to: {reply_to}",
            f"related_task: {task_id}",
            f"subject: {subject}",
            "---",
        ]
    )
    path = _sender_dir(root, sender) / f"{stem}.md"
    path.write_text(head + "\n\n" + body.rstrip() + "\n", encoding="utf-8")
    return path


def new_message(root: Path, sender: str, recipient: str, subject: str,
                body: str = "", reply_to: str = "", task_id: str = "") -> Path:
    """Programmatic API; mirrors _write_message."""
    return _write_message(root, sender, recipient, subject, body, reply_to, task_id)


def parse_message(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise MailboxError("message must start with a --- frontmatter block")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise MailboxError("frontmatter block is not closed")
    head: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        head[key.strip()] = value.strip().strip('"')
    body = "\n".join(lines[end + 1:]).strip()
    return head, body


def validate_message(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise MailboxError(f"not a file: {path}")
    head, _ = parse_message(path.read_text(encoding="utf-8"))
    missing = [f for f in REQUIRED_FIELDS if f not in head]
    if missing:
        raise MailboxError(f"{path.name}: missing fields: {', '.join(missing)}")
    # in_reply_to/related_task may be empty; the identity and routing fields
    # must be non-empty.
    for field in ("message_id", "from", "to", "created_at", "subject"):
        if head[field] == "":
            raise MailboxError(f"{path.name}: field {field!r} must not be empty")
    if head["from"] not in PARTIES or head["to"] not in PARTIES:
        raise MailboxError(f"{path.name}: unknown party in from/to")
    if head["from"] == head["to"]:
        raise MailboxError(f"{path.name}: cannot message yourself")
    if not re.fullmatch(
        r"(claude|codex|copilot)-[0-9]{8}-[0-9]{6}(-[0-9]+)?", head["message_id"]
    ):
        raise MailboxError(f"{path.name}: malformed message_id {head['message_id']!r}")
    if path.stem != head["message_id"]:
        raise MailboxError(f"{path.name}: filename stem does not match message_id")
    return head


def list_messages(root: Path, sender: str | None = None,
                  recipient: str | None = None) -> list[tuple[Path, dict[str, str]]]:
    found: list[tuple[Path, dict[str, str]]] = []
    for party in PARTIES:
        if sender is not None and party != sender:
            continue
        for path in sorted((root / f"from-{party}").glob("*.md")):
            head, _ = parse_message(path.read_text(encoding="utf-8"))
            if recipient is not None and head.get("to") != recipient:
                continue
            found.append((path, head))
    return found


def read_message(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _cmd_send(args: argparse.Namespace) -> int:
    root = mailbox_root()
    root.mkdir(exist_ok=True)
    for party in PARTIES:
        (root / f"from-{party}").mkdir(exist_ok=True)
    body = args.body
    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")
    path = _write_message(root, args.sender, args.to, args.subject, body,
                          reply_to=args.reply_to or "", task_id=args.task or "")
    print(path)
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    root = mailbox_root()
    for path, head in list_messages(root, sender=args.sender, recipient=args.to):
        print(
            f"{head['message_id']}  {head['from']}->{head['to']}  "
            f"{head['subject']}"
        )
    return 0


def _cmd_read(args: argparse.Namespace) -> int:
    root = mailbox_root()
    for path, _ in list_messages(root):
        if path.stem == args.message_id:
            sys.stdout.write(read_message(path))
            return 0
    print(f"no message with id {args.message_id}", file=sys.stderr)
    return 1


def _cmd_validate(args: argparse.Namespace) -> int:
    head = validate_message(Path(args.file))
    print(f"VALID {head['from']}->{head['to']} {head['message_id']}")
    return 0


def _cmd_log(args: argparse.Namespace) -> int:
    """Chronological transcript of the whole conversation (for the user too)."""
    root = mailbox_root()
    items: list[tuple[str, dict[str, str], str]] = []
    for party in PARTIES:
        for path in sorted((root / f"from-{party}").glob("*.md")):
            head, body = parse_message(path.read_text(encoding="utf-8"))
            items.append((head.get("created_at", ""), head, body))
    items.sort(key=lambda item: item[0])
    for _, head, body in items:
        print(
            f"=== {head['message_id']}  {head['from']} -> {head['to']}  "
            f"{head['subject']} ==="
        )
        if body:
            print(body)
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Claude<->Codex mailbox: informal async messages. "
            "Formal contract actions still use josim-handoff."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_send = sub.add_parser("send", help="send a message")
    p_send.add_argument("--to", choices=PARTIES, default="codex")
    p_send.add_argument("--from", dest="sender", choices=PARTIES, default="claude")
    p_send.add_argument("--subject", required=True)
    p_send.add_argument("--body", default="")
    p_send.add_argument("--body-file")
    p_send.add_argument("--reply-to")
    p_send.add_argument("--task")
    p_send.set_defaults(handler=_cmd_send)

    p_list = sub.add_parser("list", help="list messages")
    p_list.add_argument("--from", dest="sender", choices=PARTIES)
    p_list.add_argument("--to", choices=PARTIES)
    p_list.set_defaults(handler=_cmd_list)

    p_read = sub.add_parser("read", help="read a message by id")
    p_read.add_argument("message_id")
    p_read.set_defaults(handler=_cmd_read)

    p_val = sub.add_parser("validate", help="validate a message file")
    p_val.add_argument("file")
    p_val.set_defaults(handler=_cmd_validate)

    sub.add_parser("log", help="chronological transcript of all messages").set_defaults(
        handler=_cmd_log
    )

    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
