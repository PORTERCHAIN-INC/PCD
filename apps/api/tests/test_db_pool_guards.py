from porterchain_api import db


def test_engine_kills_stuck_transactions():
    opts = db._PG_GUARDS["options"]
    assert "idle_in_transaction_session_timeout=60000" in opts
    assert "statement_timeout=30000" in opts
