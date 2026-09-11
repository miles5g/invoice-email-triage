import json
import tempfile
import unittest
from pathlib import Path

from invoice_triage.agent import run_loop
from invoice_triage.classify import build_classifier
from invoice_triage.inbox import InboxError, load_inbox
from invoice_triage.pack import write_pack
from invoice_triage.policy import load_policy

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "data" / "inbox.json"
POLICY = ROOT / "data" / "policy.json"

EXPECTED_ACTIONS = {
    "msg-001": "approve",
    "msg-002": "approve",
    "msg-003": "request_info",
    "msg-004": "escalate",
    "msg-005": "escalate",
    "msg-006": "escalate",
    "msg-007": "request_info",
    "msg-008": "escalate",
    "msg-009": "approve",
    "msg-010": "approve",
}


class AgentLoopTest(unittest.TestCase):
    def setUp(self) -> None:
        self.messages, self.meta = load_inbox(INBOX)
        self.policy = load_policy(POLICY)

    def test_fixture_is_marked_synthetic(self) -> None:
        self.assertTrue(self.meta.get("synthetic"))
        self.assertEqual(len(self.messages), 10)

    def test_rejects_inbox_without_synthetic_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inbox.json"
            path.write_text(json.dumps({"messages": []}), encoding="utf-8")
            with self.assertRaises(InboxError):
                load_inbox(path)

    def test_loop_actions_on_demo_inbox(self) -> None:
        decisions = run_loop(self.messages, self.policy)
        got = {d.message.id: d.classification.action for d in decisions}
        self.assertEqual(got, EXPECTED_ACTIONS)

    def test_duplicate_is_detected_across_the_loop(self) -> None:
        decisions = run_loop(self.messages, self.policy)
        resend = next(d for d in decisions if d.message.id == "msg-006")
        self.assertIn("duplicate_invoice", resend.classification.labels)
        self.assertEqual(resend.classification.action, "escalate")

    def test_payment_change_escalates(self) -> None:
        decisions = run_loop(self.messages, self.policy)
        fraud = next(d for d in decisions if d.message.id == "msg-005")
        self.assertIn("payment_instruction_change", fraud.classification.labels)
        self.assertIn("unknown_vendor", fraud.classification.labels)

    def test_llm_engine_falls_back_without_key(self) -> None:
        decisions = run_loop(
            self.messages, self.policy, classifier=build_classifier("llm")
        )
        got = {d.message.id: d.classification.action for d in decisions}
        self.assertEqual(got, EXPECTED_ACTIONS)

    def test_pack_contains_disclaimer_and_all_actions(self) -> None:
        decisions = run_loop(self.messages, self.policy)
        with tempfile.TemporaryDirectory() as tmp:
            pack_path, log_path = write_pack(
                decisions,
                self.policy,
                Path(tmp),
                inbox_label="data/inbox.json",
                inbox_disclaimer=str(self.meta["disclaimer"]),
            )
            pack = pack_path.read_text(encoding="utf-8")
            self.assertIn("SYNTHETIC DEMO", pack)
            self.assertIn("approve", pack)
            self.assertIn("request_info", pack)
            self.assertIn("escalate", pack)
            log_lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(log_lines), 10)


if __name__ == "__main__":
    unittest.main()
