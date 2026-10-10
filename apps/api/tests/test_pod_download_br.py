"""BR — POD photos and the signature can be downloaded, not only viewed."""

from __future__ import annotations

import base64
import io
import uuid
import zipfile
from datetime import UTC, datetime

import pytest

from porterchain_api.reporting.pod_export import (
    PodFetchFailed,
    PodUnavailable,
    artifact_bytes,
    artifact_filename,
    build_bundle,
    find_artifact,
    list_artifacts,
    pod_error_message,
)
from porterchain_api.reporting.pod_normalize import normalize_pod, proof_slug

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8AAAwAB/wFeuwPQAAAAAElFTkSuQmCC"
)


def _gallery(*proofs: dict) -> dict:
    return normalize_pod(list(proofs))


# --- Download handles ---


def test_every_proof_gets_a_download_handle() -> None:
    gallery = _gallery(
        {"type": "photo", "url": "https://cdn.example.org/a.jpg"},
        {"type": "signature", "signature": "Jane Doe"},
    )
    assert gallery["photos"][0]["download"] == "photo-1"
    assert gallery["signatures"][0]["download"] == "signature-1"


def test_the_handle_prefers_the_fleetbase_id() -> None:
    """Gallery order can shift between the page load and the download click."""
    gallery = _gallery({"type": "photo", "url": "https://cdn.example.org/a.jpg", "id": "AB-99"})
    assert gallery["photos"][0]["download"] == "ab-99"


def test_a_handle_is_safe_to_put_in_a_url_and_a_filename() -> None:
    assert proof_slug("../../etc/passwd") == "etc-passwd"
    assert proof_slug("proof 12/34") == "proof-12-34"
    assert proof_slug("   ") is None


def test_two_proofs_never_share_a_handle() -> None:
    gallery = _gallery(
        {"type": "photo", "url": "https://cdn.example.org/a.jpg", "id": "same"},
        {"type": "photo", "url": "https://cdn.example.org/b.jpg", "id": "same"},
    )
    handles = [p["download"] for p in gallery["photos"]]
    assert len(set(handles)) == 2


def test_tracking_and_order_360_stamp_the_same_handles() -> None:
    """Both surfaces read one normalizer, so a handle works on either (BR)."""
    from porterchain_api.merchant_engine.tracking_service import _normalize_pod

    proofs = [{"type": "photo", "url": "https://cdn.example.org/a.jpg", "id": "x1"}]
    assert _normalize_pod(proofs) == normalize_pod(proofs)


# --- Listing what can be downloaded ---


def test_the_signature_is_downloadable_even_without_a_url() -> None:
    """A typed name is the evidence; there is no image to fetch."""
    gallery = _gallery({"type": "signature", "signature": "Jane Doe"})
    artifacts = list_artifacts(gallery)
    assert len(artifacts) == 1
    assert artifacts[0].is_text
    payload, media_type, extension = artifact_bytes(artifacts[0])
    assert payload == b"Jane Doe"
    assert extension == ".txt"
    assert "text/plain" in media_type


def test_a_proof_with_nothing_in_it_is_not_offered() -> None:
    gallery = _gallery({"type": "photo"}, {"type": "signature"})
    assert list_artifacts(gallery) == []


def test_an_unknown_handle_is_refused_not_guessed() -> None:
    gallery = _gallery({"type": "photo", "url": "https://cdn.example.org/a.jpg"})
    with pytest.raises(PodUnavailable):
        find_artifact(gallery, "photo-9")


def test_a_handle_from_the_gallery_resolves() -> None:
    gallery = _gallery({"type": "photo", "url": "https://cdn.example.org/a.jpg", "id": "ab-1"})
    found = find_artifact(gallery, gallery["photos"][0]["download"])
    assert found.url == "https://cdn.example.org/a.jpg"


# --- Filenames ---


def test_a_filename_starts_with_the_shipment_reference() -> None:
    """Several POD downloads land in one folder and must stay apart."""
    gallery = _gallery({"type": "photo", "url": "https://cdn.example.org/a.jpg"})
    artifact = list_artifacts(gallery)[0]
    assert artifact_filename("PC-20260911-ABC123", artifact, ".jpg") == (
        "PC-20260911-ABC123-photo-1.jpg"
    )


def test_a_filename_survives_a_missing_reference() -> None:
    gallery = _gallery({"type": "signature", "signature": "Jane"})
    artifact = list_artifacts(gallery)[0]
    assert artifact_filename(None, artifact, ".txt") == "SHIPMENT-signature-1.txt"


# --- Signature pads post data URLs, not links ---


def test_a_data_url_signature_becomes_a_real_image() -> None:
    encoded = base64.b64encode(PNG_BYTES).decode()
    gallery = _gallery({"type": "signature", "url": f"data:image/png;base64,{encoded}"})
    payload, media_type, extension = artifact_bytes(list_artifacts(gallery)[0])
    assert payload == PNG_BYTES
    assert media_type == "image/png"
    assert extension == ".png"


def test_a_corrupt_data_url_is_reported_not_saved() -> None:
    gallery = _gallery({"type": "signature", "url": "data:image/png;base64,not-base64!!"})
    with pytest.raises(PodUnavailable):
        artifact_bytes(list_artifacts(gallery)[0])


def test_a_non_http_url_is_refused() -> None:
    """A bad upstream value must not turn a download into a local file read."""
    gallery = _gallery({"type": "photo", "url": "file:///etc/passwd"})
    with pytest.raises(PodUnavailable):
        artifact_bytes(list_artifacts(gallery)[0])


# --- The bundle ---


def test_a_shipment_with_no_pod_says_so() -> None:
    with pytest.raises(PodUnavailable) as exc:
        build_bundle("PC-1", _gallery())
    assert "no proof of delivery" in pod_error_message(str(exc.value)).lower()


def test_the_bundle_holds_the_evidence_and_a_note(monkeypatch) -> None:
    _stub_media(monkeypatch, {"https://cdn.example.org/a.jpg": (PNG_BYTES, "image/png")})
    gallery = _gallery(
        {"type": "photo", "url": "https://cdn.example.org/a.jpg"},
        {"type": "signature", "signature": "Jane Doe"},
        {"type": "otp", "otp": "4471"},
    )

    archive, filename = build_bundle("PC-20260911-ABC123", gallery)
    assert filename == "PC-20260911-ABC123-proof-of-delivery.zip"

    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        names = sorted(zf.namelist())
        assert names == [
            "PC-20260911-ABC123-otp-1.txt",
            "PC-20260911-ABC123-photo-1.png",
            "PC-20260911-ABC123-proof-of-delivery.txt",
            "PC-20260911-ABC123-signature-1.txt",
        ]
        assert zf.read("PC-20260911-ABC123-photo-1.png") == PNG_BYTES
        assert zf.read("PC-20260911-ABC123-signature-1.txt") == b"Jane Doe"
        note = zf.read("PC-20260911-ABC123-proof-of-delivery.txt").decode()

    assert "PC-20260911-ABC123" in note
    assert "Photo 1" in note and "Signature 1" in note


def test_one_unreachable_photo_does_not_lose_the_rest(monkeypatch) -> None:
    """A merchant chasing a claim should get the evidence that is readable."""
    _stub_media(monkeypatch, {"https://cdn.example.org/ok.jpg": (PNG_BYTES, "image/png")})
    gallery = _gallery(
        {"type": "photo", "url": "https://cdn.example.org/ok.jpg"},
        {"type": "photo", "url": "https://cdn.example.org/gone.jpg"},
    )

    archive, _ = build_bundle("PC-1", gallery)
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        names = zf.namelist()
    assert "PC-1-photo-1.png" in names
    assert "PC-1-photo-2.png" not in names


def test_the_note_never_promises_a_file_that_is_missing(monkeypatch) -> None:
    _stub_media(monkeypatch, {"https://cdn.example.org/ok.jpg": (PNG_BYTES, "image/png")})
    gallery = _gallery(
        {"type": "photo", "url": "https://cdn.example.org/ok.jpg"},
        {"type": "photo", "url": "https://cdn.example.org/gone.jpg"},
    )
    archive, _ = build_bundle("PC-1", gallery)
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        note = zf.read("PC-1-proof-of-delivery.txt").decode()
    assert "PC-1-photo-1.png" in note
    assert "photo-2" not in note


def test_pod_that_is_recorded_but_unreachable_is_not_an_empty_zip(monkeypatch) -> None:
    _stub_media(monkeypatch, {})
    gallery = _gallery({"type": "photo", "url": "https://cdn.example.org/gone.jpg"})
    with pytest.raises(PodFetchFailed):
        build_bundle("PC-1", gallery)


def test_an_oversized_photo_is_refused(monkeypatch) -> None:
    from porterchain_api.reporting import pod_export

    _stub_media(
        monkeypatch,
        {"https://cdn.example.org/huge.jpg": (b"x" * (pod_export.MAX_ARTIFACT_BYTES + 1), "image/jpeg")},
    )
    gallery = _gallery({"type": "photo", "url": "https://cdn.example.org/huge.jpg"})
    with pytest.raises(PodFetchFailed):
        artifact_bytes(list_artifacts(gallery)[0])


# --- Error copy ---


def test_every_pod_error_reads_as_english() -> None:
    for code in (
        "pod_not_available",
        "pod_artifact_not_found",
        "pod_media_unavailable",
        "pod_media_too_large",
        "order_not_found",
    ):
        message = pod_error_message(code)
        assert message[0].isupper() and message.endswith(".")
        assert "_" not in message


def test_an_unknown_code_still_reads_as_english() -> None:
    assert pod_error_message("kaboom") == pod_error_message("pod_not_available")


# --- The routes ---


def _order(db, merchant_id: str):
    from porterchain_api.booking_models import Order
    from porterchain_api.domain.states import OrderState

    order = Order(
        merchant_id=merchant_id,
        state=OrderState.POD_COMPLETED.value,
        amount_cents=3200,
        currency="cad",
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        tracking_number=f"PC{uuid.uuid4().hex[:10].upper()}",
        pickup={"formatted": "100 King St W, Toronto"},
        dropoff={"formatted": "200 Bay St, Toronto"},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    return order


@pytest.fixture
def merchant_ctx(db):
    from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
    from porterchain_api.merchant_engine.rbac import MerchantContext
    from porterchain_api.merchant_models import Merchant, MerchantUser

    suffix = uuid.uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"POD Co {suffix}",
        email=f"pod-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_{suffix}",
        email=f"user-{suffix}@test.local",
        role=MerchantRole.OWNER.value,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)


@pytest.fixture
def merchant_client(db, monkeypatch, merchant_ctx):
    """Merchant door sharing the test transaction. Module authz has its own tests."""
    from fastapi.testclient import TestClient

    from porterchain_api.auth.merchant import get_merchant_context
    from porterchain_api.db import get_db
    from porterchain_api.main import app

    monkeypatch.setattr(
        "porterchain_api.routers.merchant.orders_tracking.require_module",
        lambda ctx, module: None,
    )
    app.dependency_overrides[get_merchant_context] = lambda: merchant_ctx
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _serve_pod(monkeypatch, gallery: dict) -> None:
    """Stand in for the live Fleetbase POD the 360 detail would fetch."""
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.orders_service.MerchantOrdersService.get_detail_360",
        lambda self, db, settings, ctx, order_id: {"proof_of_delivery": gallery},
    )


def test_the_merchant_can_download_the_whole_bundle(
    merchant_client, db, monkeypatch, merchant_ctx
) -> None:
    _stub_media(monkeypatch, {"https://cdn.example.org/a.jpg": (PNG_BYTES, "image/png")})
    order = _order(db, merchant_ctx.merchant.id)
    _serve_pod(
        monkeypatch,
        _gallery(
            {"type": "photo", "url": "https://cdn.example.org/a.jpg"},
            {"type": "signature", "signature": "Jane Doe"},
        ),
    )

    res = merchant_client.get(f"/v1/merchant/orders/{order.id}/pod.zip")
    assert res.status_code == 200, res.text
    assert res.headers["content-type"] == "application/zip"
    assert f"{order.tracking_number}-proof-of-delivery.zip" in res.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
        assert f"{order.tracking_number}-photo-1.png" in zf.namelist()


def test_the_merchant_can_download_one_photo(
    merchant_client, db, monkeypatch, merchant_ctx
) -> None:
    _stub_media(monkeypatch, {"https://cdn.example.org/a.jpg": (PNG_BYTES, "image/png")})
    order = _order(db, merchant_ctx.merchant.id)
    gallery = _gallery({"type": "photo", "url": "https://cdn.example.org/a.jpg"})
    _serve_pod(monkeypatch, gallery)

    slug = gallery["photos"][0]["download"]
    res = merchant_client.get(f"/v1/merchant/orders/{order.id}/pod/{slug}")
    assert res.status_code == 200, res.text
    assert res.content == PNG_BYTES
    assert res.headers["content-type"] == "image/png"
    assert "attachment" in res.headers["content-disposition"]


def test_the_download_is_an_attachment_not_a_page(
    merchant_client, db, monkeypatch, merchant_ctx
) -> None:
    """Without this header the browser shows the image instead of saving it."""
    _stub_media(monkeypatch, {})
    order = _order(db, merchant_ctx.merchant.id)
    gallery = _gallery({"type": "signature", "signature": "Jane Doe"})
    _serve_pod(monkeypatch, gallery)

    res = merchant_client.get(
        f"/v1/merchant/orders/{order.id}/pod/{gallery['signatures'][0]['download']}"
    )
    assert res.status_code == 200, res.text
    disposition = res.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    assert disposition.endswith(f'"{order.tracking_number}-signature-1.txt"')


def test_no_pod_yet_is_a_404_in_english(merchant_client, db, monkeypatch, merchant_ctx) -> None:
    order = _order(db, merchant_ctx.merchant.id)
    _serve_pod(monkeypatch, _gallery())

    res = merchant_client.get(f"/v1/merchant/orders/{order.id}/pod.zip")
    assert res.status_code == 404
    assert res.json()["detail"] == "There is no proof of delivery for this shipment yet."


def test_unreachable_media_is_not_reported_as_a_missing_order(
    merchant_client, db, monkeypatch, merchant_ctx
) -> None:
    """POD exists; Fleetbase is down. That is 502, not 404."""
    _stub_media(monkeypatch, {})
    order = _order(db, merchant_ctx.merchant.id)
    _serve_pod(monkeypatch, _gallery({"type": "photo", "url": "https://cdn.example.org/gone.jpg"}))

    res = merchant_client.get(f"/v1/merchant/orders/{order.id}/pod.zip")
    assert res.status_code == 502
    assert "try again" in res.json()["detail"].lower()


def test_another_companys_pod_is_not_downloadable(
    merchant_client, db, monkeypatch, merchant_ctx
) -> None:
    """The scoped order lookup must run before any media is fetched."""
    from porterchain_api.domain.merchant_states import MerchantStatus
    from porterchain_api.merchant_models import Merchant

    other = Merchant(
        status=MerchantStatus.ACTIVE.value,
        company_name="Someone Else Ltd",
        email=f"other_{uuid.uuid4().hex[:8]}@pod.test",
    )
    db.add(other)
    db.flush()
    their_order = _order(db, other.id)

    res = merchant_client.get(f"/v1/merchant/orders/{their_order.id}/pod.zip")
    assert res.status_code == 404
    assert res.json()["detail"] == "That order was not found."


def test_an_unknown_handle_is_a_404(merchant_client, db, monkeypatch, merchant_ctx) -> None:
    order = _order(db, merchant_ctx.merchant.id)
    _serve_pod(monkeypatch, _gallery({"type": "photo", "url": "https://cdn.example.org/a.jpg"}))

    res = merchant_client.get(f"/v1/merchant/orders/{order.id}/pod/photo-9")
    assert res.status_code == 404
    assert res.json()["detail"] == "That proof of delivery file was not found."


def test_downloads_name_themselves_across_origins() -> None:
    """The portals read the filename off the response, so CORS must expose it."""
    from porterchain_api.main import app

    cors = next(
        m for m in app.user_middleware if "CORSMiddleware" in str(m.cls)
    )
    assert "Content-Disposition" in cors.kwargs["expose_headers"]


# --- Test doubles ---


def _stub_media(monkeypatch, responses: dict[str, tuple[bytes, str]]) -> None:
    """Serve fake Fleetbase media so no test reaches the network."""
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        entry = responses.get(str(request.url))
        if entry is None:
            return httpx.Response(404)
        payload, media_type = entry
        return httpx.Response(200, content=payload, headers={"content-type": media_type})

    transport = httpx.MockTransport(handler)
    original = httpx.Client

    def client(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", client)
