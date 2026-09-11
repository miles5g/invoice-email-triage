from __future__ import annotations

import argparse
import sys
from pathlib import Path

from invoice_triage.agent import run_loop
from invoice_triage.classify import build_classifier
from invoice_triage.inbox import InboxError, load_inbox
from invoice_triage.pack import render_console_summary, write_pack
from invoice_triage.policy import load_policy

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INBOX = REPO_ROOT / "data" / "inbox.json"
DEFAULT_POLICY = REPO_ROOT / "data" / "policy.json"
DEFAULT_OUT = REPO_ROOT / "output"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="invoice-triage",
        description=(
            "Triage a synthetic invoice inbox: read → classify → propose action → "
            "write a human-readable pack. Offline rules by default."
        ),
    )
    parser.add_argument(
        "--inbox",
        type=Path,
        default=DEFAULT_INBOX,
        help="Synthetic inbox JSON (must set meta.synthetic=true)",
    )
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY, help="AP policy JSON")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Directory for triage_pack.md and decisions.jsonl",
    )
    parser.add_argument(
        "--engine",
        choices=("rules", "llm"),
        default="rules",
        help="rules = offline (default). llm = optional, falls back to rules without a key.",
    )
    return parser


def _display_path(path: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        messages, meta = load_inbox(args.inbox)
        policy = load_policy(args.policy)
    except (OSError, InboxError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    classifier = build_classifier(args.engine)
    decisions = run_loop(messages, policy, classifier=classifier)
    pack_path, log_path = write_pack(
        decisions,
        policy,
        args.out,
        inbox_label=_display_path(args.inbox),
        inbox_disclaimer=str(meta.get("disclaimer") or ""),
    )
    print(render_console_summary(decisions, pack_path, log_path))
    return 0
