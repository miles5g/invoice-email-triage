from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Protocol

from invoice_triage.extract import evidence_lines
from invoice_triage.models import Classification, ExtractedFields, Message, RunMemory
from invoice_triage.policy import Policy, Vendor

_MONEY = "${:,.2f}"


class Classifier(Protocol):
    engine: str

    def classify(
        self,
        message: Message,
        extracted: ExtractedFields,
        policy: Policy,
        memory: RunMemory,
    ) -> Classification: ...


class RuleClassifier:
    """Deterministic, offline policy engine. Default path — no API key."""

    engine = "rules"

    def classify(
        self,
        message: Message,
        extracted: ExtractedFields,
        policy: Policy,
        memory: RunMemory,
    ) -> Classification:
        vendor = policy.match_vendor(message)
        labels: list[str] = []
        reasons: list[str] = []
        missing = _missing_fields(extracted, policy)
        prior = memory.first_seen(extracted.invoice_number)

        if missing:
            labels.append("missing_fields")
            reasons.append("Missing required fields: " + ", ".join(missing))

        if extracted.payment_change_requested and policy.escalate_payment_instruction_change:
            labels.append("payment_instruction_change")
            reasons.append(
                "Message asks to change bank or payment instructions — treat as high risk."
            )

        if prior and extracted.invoice_number:
            labels.append("duplicate_invoice")
            reasons.append(
                f"Invoice {extracted.invoice_number} was already seen on {prior}."
            )

        if vendor is None:
            labels.append("unknown_vendor")
            reasons.append(f"Sender domain is not on the known-vendor list ({message.from_email}).")
        else:
            labels.append("known_vendor")
            reasons.append(f"Matched known vendor: {vendor.name}")
            if _is_amount_anomaly(extracted, vendor, policy):
                labels.append("amount_anomaly")
                reasons.append(
                    f"Amount {_fmt(extracted.amount_usd)} is more than "
                    f"{policy.amount_anomaly_multiplier:g}× the typical "
                    f"{_fmt(vendor.typical_amount_usd)} for {vendor.name}."
                )

        if (
            extracted.amount_usd is not None
            and extracted.amount_usd > policy.auto_approve_max_usd
        ):
            labels.append("over_approval_limit")
            reasons.append(
                f"Amount {_fmt(extracted.amount_usd)} exceeds the "
                f"{_fmt(policy.auto_approve_max_usd)} auto-approve limit."
            )

        if not missing and "known_vendor" in labels:
            labels.append("complete_invoice")

        action = _decide_action(labels, policy)
        if action == "approve":
            reasons.append(
                f"Amount {_fmt(extracted.amount_usd)} is within the "
                f"{_fmt(policy.auto_approve_max_usd)} auto-approve limit."
            )
            if extracted.invoice_number:
                reasons.append(
                    f"Invoice {extracted.invoice_number} has not been seen earlier in this run."
                )
        confidence = _confidence(action, labels)
        next_step, reply = _guidance(action, message, extracted, missing, labels, vendor)
        evidence = evidence_lines(message, extracted)

        return Classification(
            action=action,
            confidence=confidence,
            labels=labels,
            reasons=reasons,
            evidence=evidence,
            suggested_next_step=next_step,
            suggested_reply=reply,
        )


class LlmClassifier:
    """
    Optional LLM path. Uses rules unless OPENAI_API_KEY is set and the call works.
    Any failure falls back to RuleClassifier so the demo still finishes offline.
    """

    def __init__(self, fallback: Classifier | None = None) -> None:
        self.fallback = fallback or RuleClassifier()
        self.api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.engine = "llm" if self.api_key else f"{self.fallback.engine}+llm-unavailable"

    def classify(
        self,
        message: Message,
        extracted: ExtractedFields,
        policy: Policy,
        memory: RunMemory,
    ) -> Classification:
        fallback = self.fallback.classify(message, extracted, policy, memory)
        if not self.api_key:
            fallback.reasons.append(
                "LLM engine requested but OPENAI_API_KEY is unset; used offline rules."
            )
            return fallback
        try:
            llm = self._ask_llm(message, extracted, policy, fallback)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
            fallback.reasons.append(f"LLM call failed ({exc.__class__.__name__}); used offline rules.")
            return fallback
        # Keep rule labels that encode hard policy (duplicates, payment-change).
        hard = {
            label
            for label in fallback.labels
            if label
            in {
                "duplicate_invoice",
                "payment_instruction_change",
                "over_approval_limit",
            }
        }
        raw_labels = llm.get("labels") or fallback.labels
        labels = list(dict.fromkeys([*raw_labels, *hard]))
        action = llm.get("action") or fallback.action
        if action not in {"approve", "request_info", "escalate"}:
            action = fallback.action
        if hard and action == "approve":
            action = fallback.action
        return Classification(
            action=action,
            confidence=float(llm.get("confidence") or fallback.confidence),
            labels=labels,
            reasons=list(llm.get("reasons") or fallback.reasons),
            evidence=fallback.evidence,
            suggested_next_step=str(
                llm.get("suggested_next_step") or fallback.suggested_next_step
            ),
            suggested_reply=llm.get("suggested_reply") or fallback.suggested_reply,
        )

    def _ask_llm(
        self,
        message: Message,
        extracted: ExtractedFields,
        policy: Policy,
        fallback: Classification,
    ) -> dict:
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are assisting a synthetic accounts-payable triage demo. "
                        "Return JSON with keys: action (approve|request_info|escalate), "
                        "confidence (0-1), labels (array of strings), reasons (array), "
                        "suggested_next_step (string), suggested_reply (string or null). "
                        "Never invent real companies. Stay inside the provided message."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "policy": {
                                "auto_approve_max_usd": policy.auto_approve_max_usd,
                                "require_po_above_usd": policy.require_po_above_usd,
                            },
                            "message": {
                                "from": message.from_email,
                                "subject": message.subject,
                                "body": message.body,
                            },
                            "extracted": extracted.as_dict(),
                            "rule_hint": {
                                "action": fallback.action,
                                "labels": fallback.labels,
                            },
                        }
                    ),
                },
            ],
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM response was not an object")
        return parsed


def build_classifier(engine: str) -> Classifier:
    if engine == "llm":
        return LlmClassifier()
    return RuleClassifier()


def _missing_fields(extracted: ExtractedFields, policy: Policy) -> list[str]:
    missing: list[str] = []
    if policy.require_invoice_number and not extracted.invoice_number:
        missing.append("invoice_number")
    if policy.require_amount and extracted.amount_usd is None:
        missing.append("amount")
    if (
        extracted.amount_usd is not None
        and extracted.amount_usd >= policy.require_po_above_usd
        and not extracted.po_number
    ):
        missing.append("po_number")
    # Amount unknown but PO still useful? only require PO when we know the amount.
    return missing


def _is_amount_anomaly(extracted: ExtractedFields, vendor: Vendor, policy: Policy) -> bool:
    if extracted.amount_usd is None or vendor.typical_amount_usd <= 0:
        return False
    return extracted.amount_usd > vendor.typical_amount_usd * policy.amount_anomaly_multiplier


def _decide_action(labels: list[str], policy: Policy) -> str:
    escalate_labels = {
        "payment_instruction_change",
        "duplicate_invoice",
        "over_approval_limit",
        "amount_anomaly",
    }
    if policy.escalate_unknown_vendor:
        escalate_labels.add("unknown_vendor")
    if any(label in escalate_labels for label in labels):
        return "escalate"
    if "missing_fields" in labels:
        return "request_info"
    return "approve"


def _confidence(action: str, labels: list[str]) -> float:
    if "payment_instruction_change" in labels or "duplicate_invoice" in labels:
        return 0.93
    if action == "escalate" and "over_approval_limit" in labels:
        return 0.91
    if action == "escalate":
        return 0.86
    if action == "request_info":
        return 0.82
    if "complete_invoice" in labels and "known_vendor" in labels:
        return 0.90
    return 0.78


def _guidance(
    action: str,
    message: Message,
    extracted: ExtractedFields,
    missing: list[str],
    labels: list[str],
    vendor: Vendor | None,
) -> tuple[str, str | None]:
    vendor_name = vendor.name if vendor else message.from_name
    if action == "approve":
        return (
            "Ready for human confirmation, then batch payment to the vendor on file.",
            None,
        )
    if action == "request_info":
        needed = ", ".join(missing) if missing else "clarifying details"
        reply = (
            f"Hi {vendor_name},\n\n"
            f"We received '{message.subject}' but cannot post it yet. "
            f"Please resend with: {needed}.\n\n"
            "Thanks,\nAccounts Payable (demo)"
        )
        return f"Ask the vendor for: {needed}.", reply
    parts: list[str] = []
    if "payment_instruction_change" in labels:
        parts.append("Hold payment. Verify any bank-detail change out-of-band with a known contact.")
    if "duplicate_invoice" in labels:
        parts.append("Hold as a possible duplicate and compare to the earlier posting before paying.")
    if "over_approval_limit" in labels:
        parts.append("Route to an approver with authority above the auto-approve limit.")
    if "amount_anomaly" in labels:
        parts.append("Confirm the amount with the requestor — it is far from this vendor's typical bill.")
    if "unknown_vendor" in labels and "payment_instruction_change" not in labels:
        parts.append("Review before paying — sender is not on the known-vendor list.")
    step = " ".join(parts) if parts else "Escalate to AP lead for review."
    return step, None


def _fmt(amount: float | None) -> str:
    if amount is None:
        return "(none)"
    return _MONEY.format(amount)
