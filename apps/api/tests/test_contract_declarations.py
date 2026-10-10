import pytest

from porterchain_api.merchant_engine.booking_service import _check_declarations
from porterchain_api.merchant_engine.booking_validation import BookingValidationError


class B:
    def __init__(self, dg=False, prohibited=None):
        self.dangerous_goods = dg
        self.prohibited_articles = prohibited


def test_declarations_block_dg_and_prohibited():
    _check_declarations(B())
    with pytest.raises(BookingValidationError):
        _check_declarations(B(dg=True))
    with pytest.raises(BookingValidationError):
        _check_declarations(B(prohibited=["cannabis"]))
