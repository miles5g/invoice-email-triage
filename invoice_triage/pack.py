from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from invoice_triage.models import Decision
from invoice_triage.policy import Policy

_ACTIONS = ("approve", "request_info", "escalate")


def write_pack(
    decisions: list[Decision],
    policy: Policy,
    out_dir: Path,
    *,
    inbox_label: str,
    inbox_disclaimer: str,
    generated_at: datetime | None = None,
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = generated_at or datetime.now(timezone.utc)
    pack_path = out_dir / "triage_pack.md"
    log_path = out_dir / "decisions.jsonl"
    pack_path.write_text(
        render_markdown(decisions, policy, inbox_label, inbox_disclaimer, stamp),
        encoding="utf-8",
    )
    with log_path.open("w", encoding="utf-8") as handle:
        for decision in decisions:
            handle.write(json.dumps(decision.as_log_record(), sort_keys=True) + "\n")
    return pack_path, log_path


def render_markdown(
    decisions: list[Decision],
    policy: Policy,
    inbox_label: str,
    inbox_disclaimer: str,
    generated_at: datetime,
) -> str:
    counts = Counter(d.classification.action for d in decisions)
    lines: list[str] = [
        "# Invoice triage pack",
        "",
        "> **SYNTHETIC DEMO** — Every sender, client, invoice number, and dollar",
        "> amount in this file is invented. This is a portfolio walkthrough of an",
        "> ops+AI workflow pattern, not a production mailbox bot.",
        "",
        f"- Generated: {generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
        f"- Engine: `{decisions[0].engine if decisions else 'rules'}`",
        (
            f"- Policy: `{policy.name}` · auto-approve ≤ "
            f"${policy.auto_approve_max_usd:,.2f} · PO required above "
            f"${policy.require_po_above_usd:,.2f}"
        ),
        f"- Inbox: {inbox_label} ({len(decisions)} messages)",
        "",
    ]
    if inbox_disclaimer:
        lines.extend([f"- Fixture note: {inbox_disclaimer}", ""])

    lines.extend(
        [
            "## Queue snapshot",
            "",
            "| Action | Count | Messages |",
            "| --- | ---: | --- |",
        ]
    )
    for action in _ACTIONS:
        ids = [d.message.id for d in decisions if d.classification.action == action]
        lines.append(f"| {action} | {counts.get(action, 0)} | {', '.join(ids) or '—'} |")

    lines.extend(["", "## Decision log", ""])
    if not decisions:
        lines.append("_Inbox was empty._")
        return "\n".join(lines) + "\n"

    for index, decision in enumerate(decisions, start=1):
        lines.extend(_card(index, decision))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_console_summary(decisions: list[Decision], pack_path: Path, log_path: Path) -> str:
    counts = Counter(d.classification.action for d in decisions)
    width = 62
    rows = [
        "=" * width,
        " Invoice triage pack  ·  SYNTHETIC DEMO".ljust(width - 1),
        "=" * width,
        "",
        f"  {'approve':<16}{counts.get('approve', 0)}",
        f"  {'request_info':<16}{counts.get('request_info', 0)}",
        f"  {'escalate':<16}{counts.get('escalate', 0)}",
        "",
        "  Wrote:",
        f"    {pack_path}",
        f"    {log_path}",
        "=" * width,
    ]
    return "\n".join(rows)


def _card(index: int, decision: Decision) -> list[str]:
    c = decision.classification
    e = decision.extracted
    m = decision.message
    amount = f"${e.amount_usd:,.2f}" if e.amount_usd is not None else "—"
    po = e.po_number or "—"
    due = e.due_date or "—"
    invoice = e.invoice_number or "no invoice #"
    vendor = decision.vendor_name or "unlisted vendor"
    lines = [
        f"### {index}. {c.action.upper()} · {m.id} · {invoice}",
        "",
        f"**From:** {m.from_name} `<{m.from_email}>`  ",
        f"**Subject:** {m.subject}  ",
        f"**Vendor:** {vendor}  ",
        f"**Amount:** {amount} · **PO:** {po} · **Due:** {due}  ",
        f"**Confidence:** {c.confidence:.2f} · **Labels:** {', '.join(c.labels) or '—'}",
        "",
        "**Why**",
        "",
    ]
    for reason in c.reasons:
        lines.append(f"- {reason}")
    if c.evidence:
        lines.extend(["", "**Evidence**", ""])
        for snippet in c.evidence:
            lines.append(f"> {snippet}")
    lines.extend(["", f"**Proposed next step:** {c.suggested_next_step}"])
    if c.suggested_reply:
        lines.extend(["", "**Draft reply**", "", "```", c.suggested_reply, "```"])
    return lines
