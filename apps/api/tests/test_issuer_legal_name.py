"""Issuer legal name on settings defaults, invoices, statements and remittance is Porterchain Inc."""

from __future__ import annotations

import inspect

from porterchain_api.admin_engine.settings_service import DEFAULTS
from porterchain_api.merchant_engine.billing_pack import PAYEE_LEGAL_NAME
from porterchain_api.reporting import order_documents, statement

LEGAL = "Porterchain Inc."


def test_settings_default_legal_name() -> None:
    assert DEFAULTS["settings_general"]["legal_name"] == LEGAL


def test_interac_payee_legal_name() -> None:
    assert PAYEE_LEGAL_NAME == LEGAL


def test_statement_pdf_default_issuer() -> None:
    assert (
        inspect.signature(statement.statement_pdf).parameters["issuer"].default == LEGAL
    )


def test_order_documents_have_no_old_legal_name() -> None:
    source = inspect.getsource(order_documents)
    assert "Logistics Inc" not in source
    assert LEGAL in source
