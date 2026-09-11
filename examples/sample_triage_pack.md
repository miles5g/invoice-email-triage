<!-- Checked-in snapshot from `python3 -m invoice_triage`. Re-run that command to refresh output/. -->

# Invoice triage pack

> **SYNTHETIC DEMO** — Every sender, client, invoice number, and dollar
> amount in this file is invented. This is a portfolio walkthrough of an
> ops+AI workflow pattern, not a production mailbox bot.

- Generated: 2026-09-11 23:33 UTC
- Engine: `rules`
- Policy: `demo-ap-policy` · auto-approve ≤ $2,500.00 · PO required above $500.00
- Inbox: data/inbox.json (10 messages)

- Fixture note: All senders, clients, amounts, and invoice numbers are invented for this portfolio demo. Nothing here is sourced from a real mailbox, firm, or production system.

## Queue snapshot

| Action | Count | Messages |
| --- | ---: | --- |
| approve | 4 | msg-001, msg-002, msg-009, msg-010 |
| request_info | 2 | msg-003, msg-007 |
| escalate | 4 | msg-004, msg-005, msg-006, msg-008 |

## Decision log

### 1. APPROVE · msg-001 · INV-10442

**From:** Apex Office Supplies Billing `<billing@apex-office.example>`  
**Subject:** Invoice INV-10442 — September office restock  
**Vendor:** Apex Office Supplies LLC  
**Amount:** $1,240.00 · **PO:** PO-7781 · **Due:** 2026-10-08  
**Confidence:** 0.90 · **Labels:** known_vendor, complete_invoice

**Why**

- Matched known vendor: Apex Office Supplies LLC
- Amount $1,240.00 is within the $2,500.00 auto-approve limit.
- Invoice INV-10442 has not been seen earlier in this run.

**Evidence**

> Please find invoice INV-10442 for the September office restock.
> Invoice number: INV-10442
> Amount due: $1,240.00
> Purchase order: PO-7781
> Due date: 2026-10-08
> Remit to the bank on file. Packing slip is attached in this demo as text only.

**Proposed next step:** Ready for human confirmation, then batch payment to the vendor on file.

### 2. APPROVE · msg-002 · ORB-99210

**From:** Orbit Cloud Receipts `<receipts@orbit-cloud.example>`  
**Subject:** Your Orbit Cloud Hosting receipt ORB-99210  
**Vendor:** Orbit Cloud Hosting  
**Amount:** $87.50 · **PO:** — · **Due:** 2026-09-22  
**Confidence:** 0.90 · **Labels:** known_vendor, complete_invoice

**Why**

- Matched known vendor: Orbit Cloud Hosting
- Amount $87.50 is within the $2,500.00 auto-approve limit.
- Invoice ORB-99210 has not been seen earlier in this run.

**Evidence**

> Invoice number: ORB-99210
> Amount: $87.50
> Due date: 2026-09-22

**Proposed next step:** Ready for human confirmation, then batch payment to the vendor on file.

### 3. REQUEST_INFO · msg-003 · no invoice #

**From:** Brightline Telecom Billing `<billing@brightline-telecom.example>`  
**Subject:** Past-due reminder — please remit payment  
**Vendor:** Brightline Telecom  
**Amount:** $1,675.25 · **PO:** — · **Due:** —  
**Confidence:** 0.82 · **Labels:** missing_fields, known_vendor

**Why**

- Missing required fields: invoice_number, po_number
- Matched known vendor: Brightline Telecom

**Evidence**

> This is a reminder that $1,675.25 is outstanding on your Brightline Telecom account. Please pay at your earliest convenience so service is not interrupted.

**Proposed next step:** Ask the vendor for: invoice_number, po_number.

**Draft reply**

```
Hi Brightline Telecom,

We received 'Past-due reminder — please remit payment' but cannot post it yet. Please resend with: invoice_number, po_number.

Thanks,
Accounts Payable (demo)
```

### 4. ESCALATE · msg-004 · INV-CP-4401

**From:** Cedar & Pine Facilities `<ap@cedarpine.example>`  
**Subject:** Invoice INV-CP-4401 for Q3 site maintenance  
**Vendor:** Cedar & Pine Facilities  
**Amount:** $4,812.33 · **PO:** PO-3309 · **Due:** 2026-10-15  
**Confidence:** 0.91 · **Labels:** known_vendor, over_approval_limit, complete_invoice

**Why**

- Matched known vendor: Cedar & Pine Facilities
- Amount $4,812.33 exceeds the $2,500.00 auto-approve limit.

**Evidence**

> Invoice number: INV-CP-4401
> Amount due: $4,812.33
> Purchase order: PO-3309
> Due date: 2026-10-15
> Covers scheduled HVAC and grounds work for the demo campus. Amount is a normal-sized bill for this vendor but sits above the auto-approve ceiling.

**Proposed next step:** Route to an approver with authority above the auto-approve limit.

### 5. ESCALATE · msg-005 · INV-10442

**From:** QuickPay Settlement Desk `<payments@quickpay-settle.example>`  
**Subject:** URGENT: Updated banking details for invoice INV-10442  
**Vendor:** unlisted vendor  
**Amount:** — · **PO:** — · **Due:** —  
**Confidence:** 0.93 · **Labels:** missing_fields, payment_instruction_change, duplicate_invoice, unknown_vendor

**Why**

- Missing required fields: amount
- Message asks to change bank or payment instructions — treat as high risk.
- Invoice INV-10442 was already seen on msg-001.
- Sender domain is not on the known-vendor list (payments@quickpay-settle.example).

**Evidence**

> We have updated banking details on file. Please send payment for invoice INV-10442 to the new routing and account numbers below instead of the vendor on file.
> New routing: 999999999

**Proposed next step:** Hold payment. Verify any bank-detail change out-of-band with a known contact. Hold as a possible duplicate and compare to the earlier posting before paying.

### 6. ESCALATE · msg-006 · INV-10442

**From:** Apex Office Supplies Billing `<billing@apex-office.example>`  
**Subject:** Resending invoice INV-10442  
**Vendor:** Apex Office Supplies LLC  
**Amount:** $1,240.00 · **PO:** PO-7781 · **Due:** 2026-10-08  
**Confidence:** 0.93 · **Labels:** duplicate_invoice, known_vendor, complete_invoice

**Why**

- Invoice INV-10442 was already seen on msg-001.
- Matched known vendor: Apex Office Supplies LLC

**Evidence**

> Invoice number: INV-10442
> Amount due: $1,240.00
> Purchase order: PO-7781
> Due date: 2026-10-08

**Proposed next step:** Hold as a possible duplicate and compare to the earlier posting before paying.

### 7. REQUEST_INFO · msg-007 · WS-1882

**From:** Willow Street Catering `<accounts@willow-street.example>`  
**Subject:** Catering invoice WS-1882 from Thursday lunch  
**Vendor:** Willow Street Catering  
**Amount:** — · **PO:** PO-5502 · **Due:** 2026-09-30  
**Confidence:** 0.82 · **Labels:** missing_fields, known_vendor

**Why**

- Missing required fields: amount
- Matched known vendor: Willow Street Catering

**Evidence**

> Invoice number: WS-1882
> Purchase order: PO-5502
> Due date: 2026-09-30
> The total was left off this email — we will send a breakdown if you need it.

**Proposed next step:** Ask the vendor for: amount.

**Draft reply**

```
Hi Willow Street Catering,

We received 'Catering invoice WS-1882 from Thursday lunch' but cannot post it yet. Please resend with: amount.

Thanks,
Accounts Payable (demo)
```

### 8. ESCALATE · msg-008 · PT-77004

**From:** Pixel & Type Studio `<invoices@pixeltype.example>`  
**Subject:** Invoice PT-77004 — brand system (revised)  
**Vendor:** Pixel & Type Studio  
**Amount:** $9,500.00 · **PO:** PO-2100 · **Due:** 2026-10-20  
**Confidence:** 0.91 · **Labels:** known_vendor, amount_anomaly, over_approval_limit, complete_invoice

**Why**

- Matched known vendor: Pixel & Type Studio
- Amount $9,500.00 is more than 2.5× the typical $750.00 for Pixel & Type Studio.
- Amount $9,500.00 exceeds the $2,500.00 auto-approve limit.

**Evidence**

> Invoice number: PT-77004
> Amount due: $9,500.00
> Purchase order: PO-2100
> Due date: 2026-10-20

**Proposed next step:** Route to an approver with authority above the auto-approve limit. Confirm the amount with the requestor — it is far from this vendor's typical bill.

### 9. APPROVE · msg-009 · LP-3088

**From:** Lumen Print Billing `<invoices@lumen-print.example>`  
**Subject:** Invoice LP-3088 — business cards and letterhead  
**Vendor:** Lumen Print Co.  
**Amount:** $219.00 · **PO:** — · **Due:** 2026-10-01  
**Confidence:** 0.90 · **Labels:** known_vendor, complete_invoice

**Why**

- Matched known vendor: Lumen Print Co.
- Amount $219.00 is within the $2,500.00 auto-approve limit.
- Invoice LP-3088 has not been seen earlier in this run.

**Evidence**

> Invoice number: LP-3088
> Amount: $219.00
> Due date: 2026-10-01

**Proposed next step:** Ready for human confirmation, then batch payment to the vendor on file.

### 10. APPROVE · msg-010 · NH-6610

**From:** North Harbor Janitorial `<billing@north-harbor.example>`  
**Subject:** Invoice NH-6610 — September service  
**Vendor:** North Harbor Janitorial  
**Amount:** $1,890.00 · **PO:** PO-9012 · **Due:** 2026-10-10  
**Confidence:** 0.90 · **Labels:** known_vendor, complete_invoice

**Why**

- Matched known vendor: North Harbor Janitorial
- Amount $1,890.00 is within the $2,500.00 auto-approve limit.
- Invoice NH-6610 has not been seen earlier in this run.

**Evidence**

> Invoice number: NH-6610
> Amount due: $1,890.00
> Purchase order: PO-9012
> Due date: 2026-10-10
> Monthly cleaning for the demo suite. Same vendor and similar amount as usual.

**Proposed next step:** Ready for human confirmation, then batch payment to the vendor on file.
