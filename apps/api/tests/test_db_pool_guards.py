from porterchain_api import db


def test_engine_kills_stuck_transactions():
    opts = db._PG_GUARDS["options"]
    assert "idle_in_transaction_session_timeout=60000" in opts
    assert "statement_timeout=30000" in opts


def test_report_db_lifts_and_resets_statement_timeout():
    gen = db.get_report_db()
    s = next(gen)
    assert s.execute(db.text("SHOW statement_timeout")).scalar() == "5min"
    gen.close()
    with db.SessionLocal() as fresh:
        assert fresh.execute(db.text("SHOW statement_timeout")).scalar() == "30s"
