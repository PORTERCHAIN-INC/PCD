"""L93: the overdue-suspension email must use its own EN/FR text, not the generic fallback."""
from porterchain_api.notification_engine import templates as t


def test_overdue_suspension_template_is_in_templates() -> None:
    assert "merchant_account_suspended_overdue" in t.TEMPLATES
    assert t.TEMPLATE_META["merchant_account_suspended_overdue"] == {"category": "security"}


def test_overdue_suspension_renders_bilingual_body() -> None:
    ctx = {"company_name": "Acme", "invoice_number": "INV-1", "penalty_amount": "$50.00", "amount_due": "$332.50"}
    subject, text, _html = t.render_email("merchant_account_suspended_overdue", ctx)
    assert "suspended" in subject and "suspendu" in subject
    assert "INV-1" in text and "$50.00" in text and "$332.50" in text and "Bonjour Acme" in text
