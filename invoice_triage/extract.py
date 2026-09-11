from __future__ import annotations

import re

from invoice_triage.models import ExtractedFields, Message

_INVOICE_LABELED = re.compile(
    r"(?:invoice\s*(?:number|no\.?|#)?)\s*[:#-]?\s*([A-Z]{2,4}-[A-Z0-9-]+)",
    re.IGNORECASE,
)
_INVOICE_BARE = re.compile(r"\b([A-Z]{2,4}-[A-Z0-9-]{3,})\b")
_AMOUNT_LABELED = re.compile(
    r"(?:amount\s*due|total\s*due|total\s*amount|invoice\s*amount|balance\s*due|amount)\s*[:#]?\s*\$?\s*([\d,]+(?:\.\d{2})?)",
    re.IGNORECASE,
)
_AMOUNT_BARE = re.compile(r"\$\s*([\d,]+(?:\.\d{2})?)")
_PO = re.compile(
    r"(?:purchase\s+order|p\.?o\.?)\s*[:#-]?\s*(PO-[\w-]+|\d{4,})",
    re.IGNORECASE,
)
_DUE = re.compile(
    r"(?:due\s*date|payment\s+due|due)\s*[:#]?\s*(\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)

_PAYMENT_CHANGE_HINTS = (
    "updated banking",
    "update our bank",
    "new routing",
    "new account number",
    "change payment",
    "wire to a new",
    "remit to a different",
    "new bank details",
    "updated banking details",
    "please send payment to the new",
)


def extract_fields(message: Message) -> ExtractedFields:
    text = f"{message.subject}\n{message.body}"
    invoice = _first(_INVOICE_LABELED, text) or _first_invoice_token(text)
    amount = _parse_amount(_first(_AMOUNT_LABELED, text) or _first(_AMOUNT_BARE, text))
    po = _normalize_po(_first(_PO, text))
    due = _first(_DUE, text)
    payment_change = any(hint in text.lower() for hint in _PAYMENT_CHANGE_HINTS)
    return ExtractedFields(
        invoice_number=invoice.upper() if invoice else None,
        amount_usd=amount,
        po_number=po,
        due_date=due,
        payment_change_requested=payment_change,
    )


def evidence_lines(message: Message, extracted: ExtractedFields) -> list[str]:
    """Pull short quoted lines that support the extracted fields."""
    lines = [ln.strip() for ln in message.body.splitlines() if ln.strip()]
    interesting: list[str] = []
    needles = [
        extracted.invoice_number,
        extracted.po_number,
        "amount",
        "total",
        "routing",
        "bank",
        "due",
    ]
    for line in lines:
        low = line.lower()
        if any(n and str(n).lower() in low for n in needles if n):
            interesting.append(line)
        elif extracted.amount_usd is not None and f"{extracted.amount_usd:,.2f}" in line:
            interesting.append(line)
    # Preserve order, drop dupes, keep the pack readable.
    seen: set[str] = set()
    out: list[str] = []
    for line in interesting:
        if line not in seen:
            seen.add(line)
            out.append(line)
    return out[:6]


def _first(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _first_invoice_token(text: str) -> str | None:
    for match in _INVOICE_BARE.finditer(text):
        token = match.group(1).strip()
        if token.upper().startswith("PO-"):
            continue
        return token
    return None


def _parse_amount(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


def _normalize_po(raw: str | None) -> str | None:
    if not raw:
        return None
    value = raw.strip().upper()
    if not value.startswith("PO-") and value.isdigit():
        return f"PO-{value}"
    return value
