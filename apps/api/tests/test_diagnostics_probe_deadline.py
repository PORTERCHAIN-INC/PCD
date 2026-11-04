"""/system health: network probes share one short deadline; slow ones show as unreachable."""

import time

from porterchain_api.admin_engine.diagnostics_helpers import ProbeBatch, _unreachable_probe


def test_probe_batch_marks_slow_probe_unreachable_without_waiting():
    batch = ProbeBatch(
        [
            ("fast", "Fast", lambda: {"status": "healthy"}),
            ("slow", "Slow", lambda: (time.sleep(3), {"status": "healthy"})[1]),
        ]
    )
    t0 = time.monotonic()
    out = batch.collect(0.3)
    elapsed = time.monotonic() - t0
    assert elapsed < 1.0
    assert out["fast"] == ("Fast", {"status": "healthy"})
    assert out["slow"] == ("Slow", None)


def test_probe_batch_reports_exceptions_as_critical():
    out = ProbeBatch([("boom", "Boom", lambda: 1 / 0)]).collect(1.0)
    assert out["boom"][1]["status"] == "critical"


def test_unreachable_probe_shape():
    p = _unreachable_probe(1.5)
    assert p["status"] == "critical"
    assert p["details"]["reachability"] == "unreachable"
    assert "unreachable" in p["errors"][0]
    assert _unreachable_probe(1.5, local=True)["status"] == "warning"
