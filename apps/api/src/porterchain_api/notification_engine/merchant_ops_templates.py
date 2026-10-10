"""Staff-only merchant account emails (churn risk, credit hold). Email is the real channel."""

from __future__ import annotations

OPS_TEMPLATE_META: dict[str, dict[str, str]] = {
    "merchant_churn_alert": {"category": "security"},
    "merchant_credit_hold": {"category": "security"},
}
OPS_TEMPLATES: dict[str, dict[str, str]] = {
    "merchant_churn_alert": {
        "subject": "Orders stopped: {company_name}",
        "body": (
            "{company_name} has not booked for {days_since} days (usually every {usual_gap} days).\n"
            "Last 4 weeks: {last_4w} orders (prior 4 weeks: {prior_4w}).\n\n"
            "Next step: {next_action}\n\nOpen the account: {merchant_url}"
        ),
    },
    "merchant_credit_hold": {
        "subject": "Credit hold applied: {company_name}",
        "body": (
            "New bookings for {company_name} are on hold: {reason}.\n"
            "Overdue: {overdue}.\n\n"
            "Release it in Money once the Interac e-Transfer arrives.\n\nOpen the account: {merchant_url}"
        ),
    },
}
