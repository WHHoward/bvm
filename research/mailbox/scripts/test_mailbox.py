#!/usr/bin/env python3
"""Tests for the Claude<->Codex mailbox module. stdlib only."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import mailbox as mb


def make_mailbox(tmp: str) -> Path:
    root = Path(tmp) / "mailbox"
    (root / "from-claude").mkdir(parents=True)
    (root / "from-codex").mkdir(parents=True)
    return root


class FrontmatterTests(unittest.TestCase):
    def test_roundtrip_preserves_all_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_mailbox(tmp)
            msg = mb.new_message(
                root=root,
                sender="claude",
                recipient="codex",
                subject="M4 已交付",
                body="请审计 A01。",
                task_id="JH-20260809-M4-001",
            )
            raw = msg.read_text(encoding="utf-8")
            head, body = mb.parse_message(raw)
            self.assertEqual(head["from"], "claude")
            self.assertEqual(head["to"], "codex")
            self.assertEqual(head["subject"], "M4 已交付")
            self.assertEqual(head["related_task"], "JH-20260809-M4-001")
            self.assertEqual(head["in_reply_to"], "")
            self.assertIn("请审计 A01。", body)
            self.assertEqual(head["message_id"], msg.stem)

    def test_type_field_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_mailbox(tmp)
            msg = mb.new_message(
                root=root,
                sender="codex",
                recipient="claude",
                subject="M7 已签发",
                task_id="M7",
                msg_type="TASK_READY",
            )
            head, _ = mb.parse_message(msg.read_text(encoding="utf-8"))
            self.assertEqual(head["type"], "TASK_READY")
            mb.validate_message(msg)  # must pass validation

    def test_type_defaults_to_info(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_mailbox(tmp)
            msg = mb.new_message(root, "claude", "copilot", "hello")
            head, _ = mb.parse_message(msg.read_text(encoding="utf-8"))
            self.assertEqual(head["type"], "INFO")

    def test_unknown_type_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_mailbox(tmp)
            with self.assertRaises(ValueError):
                mb.new_message(
                    root=root,
                    sender="claude",
                    recipient="codex",
                    subject="bad",
                    msg_type="NOT_A_TYPE",
                )

    def test_legacy_message_without_type_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_mailbox(tmp)
            msg = mb.new_message(root, "claude", "codex", "legacy")
            raw = msg.read_text(encoding="utf-8")
            # simulate a legacy message: strip the type line entirely
            lines = [ln for ln in raw.splitlines() if not ln.startswith("type:")]
            msg.write_text("\n".join(lines) + "\n", encoding="utf-8")
            head = mb.validate_message(msg)
            self.assertNotIn("type", head)

    def test_message_id_is_unique_per_second(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_mailbox(tmp)
            a = mb.new_message(root, "claude", "codex", "a")
            b = mb.new_message(root, "claude", "codex", "b")
            self.assertNotEqual(a.stem, b.stem)

    def test_reply_to_links_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_mailbox(tmp)
            first = mb.new_message(root, "claude", "codex", "q1")
            second = mb.new_message(
                root, "codex", "claude", "a1", reply_to=first.stem
            )
            head, _ = mb.parse_message(second.read_text(encoding="utf-8"))
            self.assertEqual(head["in_reply_to"], first.stem)

    def test_self_addressing_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_mailbox(tmp)
            with self.assertRaises(ValueError):
                mb.new_message(root, "claude", "claude", "self")

    def test_unknown_party_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_mailbox(tmp)
            with self.assertRaises(ValueError):
                mb.new_message(root, "alice", "codex", "who")


class ListAndReadTests(unittest.TestCase):
    def test_list_sorts_and_filters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_mailbox(tmp)
            mb.new_message(root, "claude", "codex", "m1")
            mb.new_message(root, "codex", "claude", "m2")
            to_codex = mb.list_messages(root, recipient="codex")
            self.assertEqual([m[1]["subject"] for m in to_codex], ["m1"])
            to_claude = mb.list_messages(root, recipient="claude")
            self.assertEqual([m[1]["subject"] for m in to_claude], ["m2"])

    def test_read_returns_full_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_mailbox(tmp)
            msg = mb.new_message(
                root, "codex", "claude", "hello", body="body line\nsecond line"
            )
            text = mb.read_message(msg)
            self.assertIn("body line", text)
            self.assertIn("second line", text)


class ValidateTests(unittest.TestCase):
    def test_validate_accepts_generated_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_mailbox(tmp)
            msg = mb.new_message(root, "claude", "codex", "ok")
            mb.validate_message(msg)  # must not raise

    def test_validate_rejects_missing_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_mailbox(tmp)
            msg = mb.new_message(root, "claude", "codex", "broken")
            text = msg.read_text(encoding="utf-8").replace("subject:", "title:")
            msg.write_text(text, encoding="utf-8")
            with self.assertRaises(mb.MailboxError):
                mb.validate_message(msg)

    def test_validate_rejects_self_addressing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_mailbox(tmp)
            msg = mb.new_message(root, "claude", "codex", "bad")
            text = msg.read_text(encoding="utf-8").replace("to: codex", "to: claude")
            msg.write_text(text, encoding="utf-8")
            with self.assertRaises(mb.MailboxError):
                mb.validate_message(msg)


class CopilotPartyTests(unittest.TestCase):
    """mailbox supports copilot as a third party (2026-08-11, user request)."""

    def test_copilot_can_send_and_receive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_mailbox(tmp)
            (root / "from-copilot").mkdir()
            msg = mb.new_message(root, "copilot", "claude", "review done", body="Pilot 0 ok")
            self.assertEqual(msg.parent.name, "from-copilot")
            head, body = mb.parse_message(msg.read_text(encoding="utf-8"))
            self.assertEqual(head["from"], "copilot")
            self.assertEqual(head["to"], "claude")
            self.assertIn("Pilot 0 ok", body)
            mb.validate_message(msg)  # must not raise
            to_claude = mb.list_messages(root, recipient="claude")
            self.assertEqual([m[1]["subject"] for m in to_claude], ["review done"])


class CliTests(unittest.TestCase):
    def _cli(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(Path(__file__).with_name("mailbox.py")), *args],
            capture_output=True,
            text=True,
            env={"MAILBOX_ROOT": str(root), "PATH": "/usr/bin:/bin"},
        )

    def test_cli_log_shows_full_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_mailbox(tmp)
            self._cli(root, "send", "--to", "codex", "--subject", "q1", "--body", "问题甲")
            self._cli(root, "send", "--from", "codex", "--to", "claude", "--subject", "a1", "--body", "回答乙")
            log = self._cli(root, "log")
            self.assertEqual(log.returncode, 0, log.stderr)
            self.assertIn("q1", log.stdout)
            self.assertIn("a1", log.stdout)
            self.assertIn("问题甲", log.stdout)
            self.assertIn("回答乙", log.stdout)
            # both directions appear, sender labels are present
            self.assertIn("claude -> codex", log.stdout)
            self.assertIn("codex -> claude", log.stdout)

    def test_cli_send_list_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_mailbox(tmp)
            send = self._cli(
                root, "send", "--to", "codex", "--subject", "cli test",
                "--body", "from cli", "--task", "JH-20260809-M4-001",
            )
            self.assertEqual(send.returncode, 0, send.stderr)
            listing = self._cli(root, "list")
            self.assertEqual(listing.returncode, 0, listing.stderr)
            self.assertIn("cli test", listing.stdout)
            self.assertIn("claude->codex", listing.stdout)
            msg_id = listing.stdout.strip().splitlines()[0].split()[0]
            read = self._cli(root, "read", msg_id)
            self.assertEqual(read.returncode, 0, read.stderr)
            self.assertIn("from cli", read.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
