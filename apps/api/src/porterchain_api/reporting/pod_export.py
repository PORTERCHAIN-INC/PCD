"""Download the POD photos and signature a driver captured (BR).

This is not the compliance dossier. That is a PDF *about* the shipment (stream
P). This is the evidence itself — the photos and the signature — so a merchant
can attach it to their own customer's invoice or to a damage claim.

Fleetbase stores POD media and serves it from its own URLs, and a browser
cannot save a cross-origin file: the HTML ``download`` attribute is ignored off
origin, so the link merely opens the image in a tab. The API therefore fetches
the bytes itself and returns them as an attachment. Nothing is re-stored here —
Fleetbase stays the owner of POD media.
"""

from __future__ import annotations

import base64
import binascii
import io
import zipfile
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlparse

from porterchain_api.fleetbase_engine.pod_normalize import proof_slug

#: A phone camera shot is a few MB. Anything past this is not a POD photo, and
#: we will not hold it in memory to find out. Prefer Settings documents max when
#: a Session is available; this constant is the hard ceiling otherwise.
MAX_ARTIFACT_BYTES = 25 * 1024 * 1024
FETCH_TIMEOUT_SECONDS = 20.0


def _max_artifact_bytes() -> int:
    """Resolve download cap from platform Documents settings when DB is reachable."""
    try:
        from porterchain_api.db import SessionLocal
        from porterchain_api.admin_engine.platform_settings import document_max_bytes

        db = SessionLocal()
        try:
            return min(document_max_bytes(db), 100 * 1024 * 1024)
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        return MAX_ARTIFACT_BYTES

#: Gallery key -> singular kind, in the order a person reads the evidence.
_GALLERY_KINDS: tuple[tuple[str, str], ...] = (
    ("photos", "photo"),
    ("signatures", "signature"),
    ("otp", "otp"),
    ("other", "other"),
)

_KIND_LABELS = {
    "photo": "Photo",
    "signature": "Signature",
    "otp": "Verification code",
    "other": "Attachment",
}

_EXTENSION_BY_MEDIA_TYPE = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/heic": ".heic",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
}



class PodUnavailable(LookupError):
    """No POD on this order yet, or no artifact by that name."""


class PodFetchFailed(RuntimeError):
    """POD exists but its media could not be read right now."""


_POD_ERRORS = {
    "order_not_found": "That order was not found.",
    "pod_not_available": "There is no proof of delivery for this shipment yet.",
    "pod_artifact_not_found": "That proof of delivery file was not found.",
    "pod_artifact_unreadable": "That proof of delivery file could not be read.",
    "pod_media_unavailable": "Proof of delivery is recorded but could not be downloaded right now. Please try again shortly.",
    "pod_media_too_large": "That proof of delivery file is too large to download.",
}


def pod_error_message(code: str) -> str:
    return _POD_ERRORS.get(code, _POD_ERRORS["pod_not_available"])


@dataclass(frozen=True)
class PodArtifact:
    """One downloadable piece of proof."""

    #: Stable, client-facing handle: the Fleetbase proof id when there is one,
    #: else its position in the gallery ("photo-1").
    slug: str
    kind: str
    label: str
    #: Where Fleetbase serves the media. ``None`` for text-only evidence.
    url: str | None = None
    #: A typed signature or a verification code: the text *is* the evidence.
    text: str | None = None
    captured_at: str | None = None

    @property
    def is_text(self) -> bool:
        return self.url is None and bool(self.text)


def list_artifacts(gallery: dict[str, Any] | None) -> list[PodArtifact]:
    """Every downloadable proof in a normalized POD gallery, in reading order."""
    artifacts: list[PodArtifact] = []

    for gallery_key, kind in _GALLERY_KINDS:
        entries = (gallery or {}).get(gallery_key) or []
        if not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                continue
            url = str(entry.get("url") or "").strip() or None
            text = entry.get("signature") if kind == "signature" else entry.get("otp")
            text = str(text or "").strip() or None
            if not url and not text:
                continue

            # The normalizer stamps the handle. Position is the fallback for a
            # gallery assembled elsewhere, such as a replayed POD event payload.
            slug = proof_slug(entry.get("download")) or f"{kind}-{index}"

            artifacts.append(
                PodArtifact(
                    slug=slug,
                    kind=kind,
                    label=f"{_KIND_LABELS.get(kind, 'Attachment')} {index}",
                    url=url,
                    text=text,
                    captured_at=str(entry.get("captured_at") or "").strip() or None,
                )
            )
    return artifacts


def find_artifact(gallery: dict[str, Any] | None, slug: str) -> PodArtifact:
    """One artifact by slug. Raises ``PodUnavailable`` rather than guessing."""
    wanted = proof_slug(slug)
    for artifact in list_artifacts(gallery):
        if artifact.slug == wanted:
            return artifact
    raise PodUnavailable("pod_artifact_not_found")


# --------------------------------------------------------------------------- #
# Fetching bytes
# --------------------------------------------------------------------------- #


def _extension(media_type: str, url: str | None) -> str:
    known = _EXTENSION_BY_MEDIA_TYPE.get(media_type.split(";")[0].strip().lower())
    if known:
        return known
    suffix = ""
    if url:
        path = unquote(urlparse(url).path)
        if "." in path.rsplit("/", 1)[-1]:
            suffix = "." + path.rsplit(".", 1)[-1].lower()
    return suffix if len(suffix) <= 6 else ".bin"


def _decode_data_url(url: str) -> tuple[bytes, str]:
    """A signature pad posts ``data:image/png;base64,...`` rather than a URL."""
    header, _, payload = url.partition(",")
    media_type = header[5:].split(";")[0].strip() or "application/octet-stream"
    if ";base64" in header:
        try:
            return base64.b64decode(payload, validate=True), media_type
        except (binascii.Error, ValueError) as exc:
            raise PodUnavailable("pod_artifact_unreadable") from exc
    return unquote(payload).encode("utf-8"), media_type


def _fetch_url(url: str) -> tuple[bytes, str]:
    """Read Fleetbase-hosted media.

    The URL comes from Fleetbase's own proofs response, never from the caller,
    but the scheme is still checked: a bad upstream value must not turn this
    into a fetch of something that is not an HTTP resource.
    """
    import httpx

    if url.startswith("data:"):
        return _decode_data_url(url)
    if urlparse(url).scheme not in ("http", "https"):
        raise PodUnavailable("pod_artifact_unreadable")

    try:
        with httpx.Client(timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            payload = response.content
            media_type = response.headers.get("content-type", "application/octet-stream")
    except httpx.HTTPError as exc:
        # Fleetbase or its CDN is unreachable. That is not a missing POD.
        raise PodFetchFailed("pod_media_unavailable") from exc

    if len(payload) > _max_artifact_bytes():
        raise PodFetchFailed("pod_media_too_large")
    return payload, media_type


def artifact_bytes(artifact: PodArtifact) -> tuple[bytes, str, str]:
    """``(payload, media_type, extension)`` for one artifact."""
    if artifact.is_text:
        return str(artifact.text).encode("utf-8"), "text/plain; charset=utf-8", ".txt"
    payload, media_type = _fetch_url(str(artifact.url))
    return payload, media_type, _extension(media_type, artifact.url)


# --------------------------------------------------------------------------- #
# Filenames and the bundle
# --------------------------------------------------------------------------- #


def download_stem(reference: str | None) -> str:
    """Filenames start with the shipment reference so a Downloads folder reads."""
    stem = proof_slug(reference)
    return stem.upper() if stem else "SHIPMENT"


def artifact_filename(reference: str | None, artifact: PodArtifact, extension: str) -> str:
    return f"{download_stem(reference)}-{artifact.slug}{extension}"


def _manifest(reference: str | None, artifacts: list[PodArtifact], named: list[str]) -> str:
    lines = [
        f"Proof of delivery — {reference or 'shipment'}",
        "",
        "Captured by the driver at the drop. Files in this archive:",
        "",
    ]
    for artifact, filename in zip(artifacts, named, strict=True):
        when = f" · captured {artifact.captured_at}" if artifact.captured_at else ""
        lines.append(f"- {filename} — {artifact.label}{when}")
    lines += ["", "PorterChain"]
    return "\n".join(lines) + "\n"


def build_bundle(reference: str | None, gallery: dict[str, Any] | None) -> tuple[bytes, str]:
    """Every proof for one shipment as a ZIP, plus a note saying what is inside.

    Raises ``PodUnavailable`` when the shipment has no POD, so the caller can
    say so in English instead of handing back an empty archive.
    """
    artifacts = list_artifacts(gallery)
    if not artifacts:
        raise PodUnavailable("pod_not_available")

    buffer = io.BytesIO()
    included: list[PodArtifact] = []
    names: list[str] = []
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for artifact in artifacts:
            try:
                payload, _, extension = artifact_bytes(artifact)
            except PodFetchFailed:
                # One unreachable photo must not deny the merchant the rest of
                # the evidence. The manifest lists only what is really inside.
                continue
            filename = artifact_filename(reference, artifact, extension)
            archive.writestr(filename, payload)
            included.append(artifact)
            names.append(filename)

        if not included:
            raise PodFetchFailed("pod_media_unavailable")
        archive.writestr(
            f"{download_stem(reference)}-proof-of-delivery.txt",
            _manifest(reference, included, names),
        )

    return buffer.getvalue(), f"{download_stem(reference)}-proof-of-delivery.zip"
