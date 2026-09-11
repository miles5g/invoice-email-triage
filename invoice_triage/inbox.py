from __future__ import annotations

import json
from pathlib import Path

from invoice_triage.models import Message


class InboxError(ValueError):
    pass


def load_inbox(path: Path) -> tuple[list[Message], dict]:
    """Load a synthetic inbox JSON file. Refuses unmarked real-looking dumps."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    meta = raw.get("meta") or {}
    if not meta.get("synthetic"):
        raise InboxError(
            f"{path} is missing meta.synthetic=true. This demo only accepts "
            "explicitly synthetic fixtures."
        )
    messages = []
    for item in raw.get("messages") or []:
        messages.append(
            Message(
                id=str(item["id"]),
                received_at=str(item["received_at"]),
                from_name=str(item["from_name"]),
                from_email=str(item["from_email"]),
                subject=str(item["subject"]),
                body=str(item["body"]),
            )
        )
    return messages, meta
