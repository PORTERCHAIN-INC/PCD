"""G10 (doc 60 §1): retired vendors have 0 mentions outside docs/.

Mirrors ``git grep -il <pattern>`` over the working tree without git: skips docs/, generated
and dependency folders, lockfiles and binary files. One entry per finished doc 60 batch; a
vendor is added here when its batch lands. Guard files that assert absence are exempt.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]

_SKIP_DIRS = {
    ".git", "docs", "node_modules", ".next", ".venv", "venv", "__pycache__", ".pytest_cache",
    "graphify-out", "dist", "build", ".turbo", ".expo", "coverage", "ios", "android",
    ".mypy_cache", ".ruff_cache", "test-results", "playwright-report",
}
_SKIP_FILES = {"pnpm-lock.yaml", "package-lock.json", "yarn.lock", "uv.lock", "poetry.lock"}
_TEXT_SUFFIXES = {
    ".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".json", ".yml", ".yaml", ".toml", ".sh",
    ".md", ".mdc", ".env", ".example", ".txt", ".ini", ".cfg", ".conf", "",
}

# vendor -> (regex, exempt repo-relative paths)
VENDORS: dict[str, tuple[str, set[str]]] = {
    "doppler": (
        r"doppler",
        {
            "apps/api/tests/test_g10_vendor_removal.py",
            "scripts/verify_enterprise_security.py",  # asserts deploy.yml has no Doppler
            "scripts/verify-secrets-alignment.sh",  # warns if the old GitHub secret is still set
        },
    ),
    # Doc 60 R7: Twilio → push + email (+ Keycloak TOTP for staff).
    "twilio": (r"twilio", {"apps/api/tests/test_g10_vendor_removal.py"}),
    # Doc 60 R4: MapLibre + self-hosted PMTiles + Photon. Narrow carve-out for the capped
    # server-side Google Places (New) Photon backup only (geo_google.py + wiring/env).
    # Distance Matrix, Maps JS, browser Places widgets, and Mapbox stay banned elsewhere.
    "google-maps": (
        r"maps\.googleapis|places\.googleapis|@googlemaps|react-google-maps|react-native-maps"
        r"|geo_google|GOOGLE_MAPS_|PROVIDER_GOOGLE|Google Maps Platform|mapbox",
        {
            "apps/api/tests/test_g10_vendor_removal.py",
            "apps/api/src/porterchain_api/geo_google.py",
            "apps/api/src/porterchain_api/geo_resolve.py",  # capped backup wiring (#182)
            "apps/api/tests/test_geo_resolve.py",
            "apps/api/src/porterchain_api/routers/geo.py",
            "apps/api/src/porterchain_api/admin_engine/integration_health.py",
            "apps/api/tests/test_geo_photon_coverage.py",
            "apps/api/tests/test_geo_google_fallback.py",
            "apps/api/tests/test_hs20_google_places_no_distance_matrix.py",
            "infrastructure/deploy/docker-compose.prod.yml",
            "env/api.env.example",
            "env/production.env.example",
            "env/compose.env.example",
            "apps/api/env.example",
            "apps/api/.env.example",
            # Encrypted inventory may keep retired key *names* (values are ciphertext).
            "secrets/droplet.enc.yaml",
        },
    ),
    # Doc 60 R2: FEATURE_AI=false; OpenAI-compatible / NVIDIA NIM clients and keys deleted.
    "openai-nvidia": (
        r"openai|nvidia|nim_client",
        {
            "apps/api/tests/test_g10_vendor_removal.py",
            "opencode.json",  # local dev tool config (Ollama on 127.0.0.1), not shipped
        },
    ),
    # Doc 60 R2: no external AI vendors at all. The website Capacity Guide is rule-based.
    "external-ai": (
        r"\bgroq\b|GROQ_|anthropic|@ai-sdk/(?!react\b|provider)|generativelanguage\.googleapis"
        r"|GEMINI_API|api\.mistral\.ai|api\.cohere|together\.xyz|api\.replicate",
        {
            "apps/api/tests/test_g10_vendor_removal.py",
            "opencode.json",  # local dev tool config, not shipped
        },
    ),
    # GlitchTip speaks the Sentry protocol: the SDK may be imported only by the two wrappers
    # below and listed as a dependency. No sentry.io DSN, host or SENTRY_DSN key anywhere.
    "sentry-sdk": (
        r"sentry_sdk|@sentry/",
        {
            "apps/api/tests/test_g10_vendor_removal.py",
            "apps/api/src/porterchain_api/platform/observability.py",
            "packages/config/glitchtip/portal.ts",
            "apps/api/pyproject.toml",
            "apps/api/requirements.txt",
            "apps/api/requirements.lock.txt",
            "packages/config/package.json",
            "apps/admin/package.json",
            "apps/customer/package.json",
            "apps/driver-portal/package.json",
            "apps/merchant-portal/package.json",
            "website/package.json",
            "pnpm-workspace.yaml",
            "website/pnpm-workspace.docker.yaml",
            ".github/dependabot.yml",
        },
    ),
    "sentry-saas": (
        r"ingest\.(us\.|de\.)?sentry\.io|(?<!LEGACY_)\bSENTRY_DSN\b",
        {
            "apps/api/tests/test_g10_vendor_removal.py",
            "scripts/verify-secrets-alignment.sh",  # warns if old GitHub secrets are still set
        },
    ),
}


def _files():
    for p in REPO.rglob("*"):
        rel = p.relative_to(REPO)
        if any(part in _SKIP_DIRS for part in rel.parts[:-1]):
            continue
        if not p.is_file() or p.name in _SKIP_FILES or p.suffix not in _TEXT_SUFFIXES:
            continue
        if p.name.startswith(".env") and not p.name.endswith(".example"):
            continue  # local secret files: never read
        if p.stat().st_size > 2_000_000:
            continue
        yield rel, p


@pytest.mark.parametrize("vendor", sorted(VENDORS))
def test_g10_vendor_absent_outside_docs(vendor: str) -> None:
    pattern, exempt = VENDORS[vendor]
    rx = re.compile(pattern, re.I)
    hits = [
        str(rel)
        for rel, p in _files()
        if str(rel) not in exempt and rx.search(p.read_text(errors="ignore"))
    ]
    assert hits == [], f"{vendor} still mentioned in: {hits}"


def test_doppler_replaced_by_sops_in_deploy() -> None:
    deploy = (REPO / ".github/workflows/deploy.yml").read_text()
    assert "./.github/actions/stage-sops-env" in deploy
    assert "secrets.SOPS_AGE_KEY" in deploy
    action = (REPO / ".github/actions/stage-sops-env/action.yml").read_text()
    assert "sops -d --output-type dotenv" in action
    assert not (REPO / ".github/actions/stage-doppler-env").exists()
    sync = (REPO / "infrastructure/deploy/sync-secrets.sh").read_text()
    assert "runtime.env" in sync and "SOPS_SECRETS_FILE" in sync


def test_glitchtip_dsn_wiring() -> None:
    from porterchain_api.config import Settings

    assert Settings(glitchtip_dsn="https://k@errors.example.test/1").glitchtip_dsn.endswith("/1")
    compose = (REPO / "infrastructure/deploy/docker-compose.prod.yml").read_text()
    assert "GLITCHTIP_DSN: ${GLITCHTIP_DSN:-}" in compose
    for app in ("apps/admin", "apps/customer", "apps/driver-portal", "apps/merchant-portal", "website"):
        assert (REPO / app / "glitchtip.server.config.ts").exists(), app
        assert not (REPO / app / "sentry.server.config.ts").exists(), app
        assert "ARG NEXT_PUBLIC_GLITCHTIP_DSN" in (REPO / app / "Dockerfile").read_text(), app


def test_feature_ai_off_and_no_llm_client() -> None:
    import importlib.util

    from porterchain_api.intelligence_engine.llm import chat_completion, llm_status

    assert importlib.util.find_spec("porterchain_api.intelligence_engine.nim_" + "client") is None
    assert llm_status()["configured"] is False
    compose = (REPO / "infrastructure/deploy/docker-compose.prod.yml").read_text()
    assert 'FEATURE_AI: "false"' in compose
    try:
        chat_completion(messages=[])
    except ValueError as exc:
        assert str(exc) == "llm_disabled"
    else:  # pragma: no cover
        raise AssertionError("LLM call must be impossible in Phase 0")


def test_capacity_guide_is_rule_based() -> None:
    route = (REPO / "website/src/app/api/capacity-guide/route.ts").read_text()
    assert "guide-rules" in route and "streamText" not in route
    assert not (REPO / "website/src/lib/home/guide-llm.ts").exists()
    pkg = (REPO / "website/package.json").read_text()
    assert "@ai-sdk/" + "groq" not in pkg



def test_g10_google_maps_abuse_still_banned() -> None:
    """Server Places backup is carved out; Distance Matrix / browser Maps SDK stay forbidden."""
    pattern, exempt = VENDORS["google-maps"]
    abuse = (
        "https://maps.googleapis.com/maps/api/distancematrix/json",
        "https://places.googleapis.com/v1/places:autocomplete",
        "import { useLoadScript } from '@react-google-maps/api'",
        "PROVIDER_GOOGLE",
        "GOOGLE_MAPS_BROWSER_KEY=x",
        "from porterchain_api import geo_google",
    )
    rx = re.compile(pattern, re.I)
    for sample in abuse:
        assert rx.search(sample), sample
    # Non-exempt product/code paths must not grow Google Maps client/Distance Matrix usage.
    for rel, p in _files():
        if str(rel) in exempt:
            continue
        body = p.read_text(errors="ignore")
        low = body.lower()
        assert "maps.googleapis.com/maps/api/distancematrix" not in low, rel
        assert "@react-google-maps" not in body, rel
        assert "react-native-maps" not in body, rel
        assert "PROVIDER_GOOGLE" not in body, rel
