"""Pass 6: empty receipt link line dropped; driver admin message has its own subject."""
from porterchain_api.notification_engine.templates import render_email


def test_receipt_without_url_has_no_empty_view_line():
    _s, text, _h = render_email("payment_receipt", {"order_number": "ORD-1", "amount_display": "$1.00 CAD", "receipt_number": "RCP-1"})
    assert "View:" not in text and "Receipt: RCP-1" in text


def test_driver_admin_message_subject():
    s, text, _h = render_email("driver_admin_message", {"message": "Your background check was verified."})
    assert s == "Message from PorterChain" and "background check" in text
