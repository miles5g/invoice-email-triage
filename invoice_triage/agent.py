from __future__ import annotations

from invoice_triage.classify import Classifier, RuleClassifier
from invoice_triage.extract import extract_fields
from invoice_triage.models import Decision, Message, RunMemory
from invoice_triage.policy import Policy


def run_loop(
    messages: list[Message],
    policy: Policy,
    classifier: Classifier | None = None,
) -> list[Decision]:
    """Read → extract → classify → log, carrying memory across messages."""
    engine = classifier or RuleClassifier()
    memory = RunMemory()
    decisions: list[Decision] = []

    for message in messages:
        extracted = extract_fields(message)
        vendor = policy.match_vendor(message)
        classification = engine.classify(message, extracted, policy, memory)
        decisions.append(
            Decision(
                message=message,
                extracted=extracted,
                classification=classification,
                vendor_id=vendor.id if vendor else None,
                vendor_name=vendor.name if vendor else None,
                engine=getattr(engine, "engine", "rules"),
            )
        )
        memory.remember(extracted.invoice_number, message.id)

    return decisions
