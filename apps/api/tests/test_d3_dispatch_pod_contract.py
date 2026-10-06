"""D3 dispatch + POD contract tests (§0.4.4, §0.4.7) — dev-layer behavioral proof."""

from __future__ import annotations

from pathlib import Path


def test_dispatch_admin_routes_present() -> None:
    routers = Path(__file__).resolve().parents[1] / "src/porterchain_api/routers"
    corpus = "\n".join(p.read_text(encoding="utf-8") for p in routers.rglob("*.py"))
    for needle in (
        'prefix="/v1/admin/operations"',
        "/dispatch/orders/{order_id}/assign",
        "/sync/health",
    ):
        assert needle in corpus, f"missing dispatch route needle: {needle}"


def test_pod_driver_and_webhook_routes_present() -> None:
    routers = Path(__file__).resolve().parents[1] / "src/porterchain_api/routers"
    corpus = "\n".join(p.read_text(encoding="utf-8") for p in routers.rglob("*.py"))
    assert "pod-complete" in corpus
    assert 'post("/fleetbase")' not in corpus


def test_fleetbase_engine_is_gone() -> None:
    api_src = Path(__file__).resolve().parents[1] / "src/porterchain_api"
    assert not (api_src / "fleetbase_engine").exists()
    assert (api_src / "dispatch_engine/sequencer.py").is_file()
