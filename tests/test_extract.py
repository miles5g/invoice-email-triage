import unittest

from invoice_triage.extract import extract_fields
from invoice_triage.models import Message


def _msg(body: str, subject: str = "Invoice") -> Message:
    return Message(
        id="t",
        received_at="2026-09-01T00:00:00Z",
        from_name="Test",
        from_email="billing@apex-office.example",
        subject=subject,
        body=body,
    )


class ExtractTest(unittest.TestCase):
    def test_labeled_fields(self) -> None:
        extracted = extract_fields(
            _msg(
                "Invoice number: INV-10442\nAmount due: $1,240.00\n"
                "Purchase order: PO-7781\nDue date: 2026-10-08\n"
            )
        )
        self.assertEqual(extracted.invoice_number, "INV-10442")
        self.assertEqual(extracted.amount_usd, 1240.0)
        self.assertEqual(extracted.po_number, "PO-7781")
        self.assertEqual(extracted.due_date, "2026-10-08")
        self.assertFalse(extracted.payment_change_requested)

    def test_does_not_treat_po_as_invoice(self) -> None:
        extracted = extract_fields(_msg("Please quote purchase order PO-7781 on the check."))
        self.assertIsNone(extracted.invoice_number)
        self.assertEqual(extracted.po_number, "PO-7781")

    def test_flags_payment_instruction_change(self) -> None:
        extracted = extract_fields(
            _msg("We have updated banking details. New routing: 999999999.")
        )
        self.assertTrue(extracted.payment_change_requested)


if __name__ == "__main__":
    unittest.main()
