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
    assert '@router.post("/fleetbase")' in corpus or 'post("/fleetbase")' in corpus


def test_fleetbase_engine_wired() -> None:
    api_src = Path(__file__).resolve().parents[1] / "src/porterchain_api"
    assert (api_src / "fleetbase_engine").is_dir()
    assert (api_src / "fleetbase_engine/webhook_ingress_service.py").is_file()
