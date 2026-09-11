from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from invoice_triage.models import Message


@dataclass(frozen=True)
class Vendor:
    id: str
    name: str
    domains: tuple[str, ...]
    typical_amount_usd: float


@dataclass(frozen=True)
class Policy:
    name: str
    auto_approve_max_usd: float
    require_po_above_usd: float
    require_invoice_number: bool
    require_amount: bool
    escalate_payment_instruction_change: bool
    escalate_unknown_vendor: bool
    amount_anomaly_multiplier: float
    vendors: tuple[Vendor, ...]

    def match_vendor(self, message: Message) -> Vendor | None:
        domain = ""
        if "@" in message.from_email:
            domain = message.from_email.rsplit("@", 1)[1].lower()
        for vendor in self.vendors:
            if domain in vendor.domains:
                return vendor
        return None


def load_policy(path: Path) -> Policy:
    raw = json.loads(path.read_text(encoding="utf-8"))
    vendors = tuple(
        Vendor(
            id=str(item["id"]),
            name=str(item["name"]),
            domains=tuple(d.lower() for d in item.get("domains") or []),
            typical_amount_usd=float(item["typical_amount_usd"]),
        )
        for item in raw.get("known_vendors") or []
    )
    return Policy(
        name=str(raw.get("name") or "unnamed-policy"),
        auto_approve_max_usd=float(raw["auto_approve_max_usd"]),
        require_po_above_usd=float(raw["require_po_above_usd"]),
        require_invoice_number=bool(raw.get("require_invoice_number", True)),
        require_amount=bool(raw.get("require_amount", True)),
        escalate_payment_instruction_change=bool(
            raw.get("escalate_payment_instruction_change", True)
        ),
        escalate_unknown_vendor=bool(raw.get("escalate_unknown_vendor", True)),
        amount_anomaly_multiplier=float(raw.get("amount_anomaly_multiplier", 2.5)),
        vendors=vendors,
    )
