from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Action = Literal["approve", "request_info", "escalate"]


@dataclass(frozen=True)
class Message:
    id: str
    received_at: str
    from_name: str
    from_email: str
    subject: str
    body: str


@dataclass
class ExtractedFields:
    invoice_number: str | None = None
    amount_usd: float | None = None
    po_number: str | None = None
    due_date: str | None = None
    payment_change_requested: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Classification:
    action: Action
    confidence: float
    labels: list[str]
    reasons: list[str]
    evidence: list[str]
    suggested_next_step: str
    suggested_reply: str | None = None


@dataclass
class Decision:
    message: Message
    extracted: ExtractedFields
    classification: Classification
    vendor_id: str | None = None
    vendor_name: str | None = None
    engine: str = "rules"

    def as_log_record(self) -> dict[str, Any]:
        return {
            "message_id": self.message.id,
            "received_at": self.message.received_at,
            "from_email": self.message.from_email,
            "from_name": self.message.from_name,
            "subject": self.message.subject,
            "action": self.classification.action,
            "confidence": self.classification.confidence,
            "labels": self.classification.labels,
            "reasons": self.classification.reasons,
            "evidence": self.classification.evidence,
            "extracted": self.extracted.as_dict(),
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor_name,
            "suggested_next_step": self.classification.suggested_next_step,
            "suggested_reply": self.classification.suggested_reply,
            "engine": self.engine,
        }


@dataclass
class RunMemory:
    """Cross-message state for one agent-loop run (duplicate detection)."""

    seen_invoices: dict[str, str] = field(default_factory=dict)

    def remember(self, invoice_number: str | None, message_id: str) -> None:
        if invoice_number and invoice_number not in self.seen_invoices:
            self.seen_invoices[invoice_number] = message_id

    def first_seen(self, invoice_number: str | None) -> str | None:
        if not invoice_number:
            return None
        return self.seen_invoices.get(invoice_number)
