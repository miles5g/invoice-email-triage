# Invoice / Email Triage Agent (synthetic demo)

**Portfolio demo** of an ops+AI workflow pattern: an agent loop that reads a fake AP inbox, classifies each message, proposes an action, logs the decision, and emits a human-readable triage pack.

This is **not** a production mailbox bot. It does not connect to email, banks, or any live system.

## Status

Runnable. One command against synthetic fixtures writes `output/triage_pack.md`.

## What it shows

1. Load a **synthetic** inbox of invoice / billing emails
2. Agent loop: **read → extract → classify → propose action → log**
3. Actions: **approve** / **request info** / **escalate**
4. A triage pack a human could review, plus a JSONL decision log

Default engine is **rule-based and offline**. No API key required.

## Hard rules

- **Synthetic data only** — invented vendors, `.example` domains, fake invoice numbers, and made-up dollar amounts
- No real firm, client, mailbox, or production figures (including Gursey or any live AP inbox)
- Demo of a workflow pattern, not an unattended payment robot

## Quickstart

Python 3.10+ (stdlib only — no `pip install` needed).

```bash
git clone https://github.com/miles5g/invoice-email-triage.git
cd invoice-email-triage
python3 -m invoice_triage
```

Equivalent:

```bash
python3 run.py
```

That writes:

- `output/triage_pack.md` — human-readable queue + decision cards
- `output/decisions.jsonl` — one logged decision per message

```bash
python3 -m unittest discover -s tests -v
```

## How the loop works

```
inbox.json  ──►  for each message
                    ├─ extract invoice # / amount / PO / risk hints
                    ├─ apply demo AP policy (limits, known vendors)
                    ├─ remember invoice numbers already seen
                    └─ decide: approve | request_info | escalate
               ──►  triage pack + JSONL log
```

Policy lives in `data/policy.json` so the “ops” half is visible: auto-approve ceiling, PO threshold, known-vendor list, and escalate-on-payment-change.

The bundled inbox is written to exercise every path:

| Message | What it is | Expected action |
| --- | --- | --- |
| `msg-001` | Complete known-vendor invoice under the limit | approve |
| `msg-002` | Small complete subscription receipt | approve |
| `msg-003` | Dunning note missing invoice # and PO | request_info |
| `msg-004` | Complete invoice above auto-approve | escalate |
| `msg-005` | Unknown sender + “new bank details” | escalate |
| `msg-006` | Resend of an invoice already seen | escalate |
| `msg-007` | Known vendor, amount omitted | request_info |
| `msg-008` | Amount far above that vendor’s typical bill | escalate |
| `msg-009` | Small complete print invoice | approve |
| `msg-010` | Complete monthly services invoice | approve |

## Optional LLM path

Works **without** keys. If you pass `--engine llm` and `OPENAI_API_KEY` is unset (or the call fails), the run falls back to the same offline rules.

```bash
python3 -m invoice_triage --engine llm
```

Do not commit secrets. A `.env` file is gitignored.

## What this is not

- Not wired to Gmail, Outlook, or a real AP system
- Not authorized to pay anyone
- Not trained on, or evaluated against, real client mail

A checked-in snapshot of a pack is in [`examples/sample_triage_pack.md`](examples/sample_triage_pack.md) so the GitHub view matches a local run.

## Author

Miles Johnson — [@miles5g](https://github.com/miles5g)
