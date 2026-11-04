"""New-device email code (Keycloak email-otp-authenticator, Unlicense): realm-as-code + theme + local-stack invariants."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
KC = ROOT / "infrastructure" / "keycloak"
THEME = KC / "themes" / "porterchain"
JAR = KC / "providers" / "email-otp-authenticator-v1.8.1-kc-26.8.1.jar"


def _realm() -> dict:
    spec = importlib.util.spec_from_file_location("build_realm", KC / "build_realm.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.realm()


def _flow(r: dict, alias: str) -> dict:
    return next(f for f in r["authenticationFlows"] if f["alias"] == alias)


def _cfg(r: dict, alias: str) -> dict:
    return next(c["config"] for c in r["authenticatorConfig"] if c["alias"] == alias)


def test_new_device_code_is_conditional_and_skips_staff():
    r = _realm()
    forms = _flow(r, "pc-forms")["authenticationExecutions"]
    sub = next(e for e in forms if e.get("flowAlias") == "pc-new-device-code")
    assert sub["requirement"] == "CONDITIONAL"
    ex = _flow(r, "pc-new-device-code")["authenticationExecutions"]
    assert [e.get("authenticator") for e in ex] == ["conditional-user-role", "email-otp-form"]
    assert all(e["requirement"] == "REQUIRED" for e in ex)
    # staff (mfa_required) are excluded; the staff TOTP subflow uses the same role un-negated
    assert _cfg(r, "pc-not-staff") == {"condUserRole": "mfa_required", "negate": "true"}
    assert _cfg(r, "pc-mfa-role") == {"condUserRole": "mfa_required", "negate": "false"}
    staff = [e.get("authenticator") for e in _flow(r, "pc-staff-otp")["authenticationExecutions"]]
    assert "auth-otp-form" in staff and "email-otp-form" not in staff


def test_code_only_on_new_device_not_every_login():
    c = _cfg(_realm(), "pc-new-device-code-cfg")
    assert c["device-trust-enabled"] == "true" and int(c["device-trust-duration"]) > 0
    assert c["trust-only-when-sole"] == "false"  # trust applies in our multi-step flow
    assert c["ip-trust-enabled"] == "false"  # shared IPs must not skip the code
    assert c["code-length"] == "6" and set(c["code-alphabet"]) <= set("0123456789")
    assert int(c["resend-cooldown"]) >= 30 and 0 < int(c["issuance-limit"]) <= 10


def test_committed_realm_has_the_flow():
    r = json.loads((KC / "realm-porterchain.json").read_text())
    assert any(f["alias"] == "pc-new-device-code" for f in r["authenticationFlows"])


def test_render_can_drop_flow_for_stock_image(tmp_path):
    out = tmp_path / "r.json"
    env = {**os.environ, "EMAIL_OTP_ENABLED": "false", "ALLOW_PLACEHOLDERS": "true"}
    subprocess.run(["bash", str(KC / "render-realm.sh"), str(out)], check=True, env=env, capture_output=True)
    r = json.loads(out.read_text())
    assert "pc-new-device-code" not in json.dumps(r)
    assert "email-otp-form" not in json.dumps(r)


def test_form_template_always_trusts_device_and_has_no_checkbox():
    ftl = (THEME / "login" / "login-email-otp.ftl").read_text()
    assert 'name="trust-device" value="true"' in ftl and 'type="checkbox"' not in ftl
    assert 'name="email-otp"' in ftl and 'autocomplete="one-time-code"' in ftl and "resend-email" in ftl
    assert 'pcPage == "login-email-otp"' in (THEME / "login" / "template.ftl").read_text()


def _props(p: Path) -> set[str]:
    return {ln.split("=", 1)[0] for ln in p.read_text().splitlines() if "=" in ln and not ln.startswith("#")}


def test_en_fr_strings_complete():
    for kind, keys in (
        ("login", {"pcCodeTitle", "pcCodeSubtitle", "pcCodeNoEmail", "loginEmailOtp", "doResendEmail", "errorInvalidEmailOtp"}),
        ("email", {"emailOtpSubject", "pcOtpHeading", "pcOtpIntro", "pcOtpExpires", "pcOtpNotYou"}),
    ):
        en, fr = (_props(THEME / kind / "messages" / f"messages_{l}.properties") for l in ("en", "fr"))
        assert keys <= en and keys <= fr, kind
    for f in ("html/otp-email.ftl", "text/otp-email.ftl"):
        t = (THEME / "email" / f).read_text()
        assert "${otp}" in t and "pcOtpHeading" in t


def test_no_clerk_name_in_new_theme_files():
    for p in [THEME / "login" / "login-email-otp.ftl", *(THEME / "email").rglob("*")]:
        if p.is_file():
            assert "clerk" not in p.read_text().lower(), p


def test_jar_pinned_by_sha256_in_local_stack():
    sh = (ROOT / "scripts" / "local-stack.sh").read_text()
    pinned = re.search(r"EOTP_SHA256=([0-9a-f]{64})", sh).group(1)
    assert JAR.name in sh
    if JAR.exists():  # jar is a downloaded binary; CI may not have it
        assert hashlib.sha256(JAR.read_bytes()).hexdigest() == pinned


def test_rate_limited_subtitle_does_not_claim_sent():
    t = (THEME / "login" / "template.ftl").read_text()
    assert 'msg("errorTooManyRequestsEmailOtp")' in t and "pcCodeSubtitleLimited" in t
    for l in ("en", "fr"):
        assert "pcCodeSubtitleLimited" in _props(THEME / "login" / "messages" / f"messages_{l}.properties")
