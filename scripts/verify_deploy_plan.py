#!/usr/bin/env python3
"""Guard: deploy-rules.json is the only scope SSOT. Prevents invented scopes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from resolve_deploy_plan import (  # noqa: E402
    IMAGE_ORDER,
    RULES_PATH,
    build_plan,
    load_rules,
)

DEPLOY_YML = ROOT / ".github/workflows/deploy.yml"


GOLDEN = (
    (["apps/merchant-portal/src/middleware.ts"], "auto", "merchant", ["merchant"], False, "partial"),
    (["apps/api/src/porterchain_api/routers/shopify.py"], "auto", "api", ["api"], True, "partial"),
    (
        ["apps/merchant-portal/src/a.tsx", "apps/admin/src/b.tsx"],
        "auto",
        "portals",
        ["admin", "merchant"],
        False,
        "partial",
    ),
    (
        ["apps/api/src/x.py", "apps/merchant-portal/src/y.tsx"],
        "auto",
        "selected",
        ["api", "merchant"],
        True,
        "partial",
    ),
    (["packages/ui/src/button.tsx"], "auto", "full", list(IMAGE_ORDER), True, "full"),
    (["docs/RUNBOOK.md"], "auto", "none", [], False, "none"),
    ([], "auto", "full", list(IMAGE_ORDER), True, "full"),
    (["totally/unknown/path.py"], "auto", "full", list(IMAGE_ORDER), True, "full"),
    (["apps/api/src/x.py"], "merchant", "merchant", ["merchant"], False, "partial"),
    (
        ["website/src/app/page.tsx", "apps/merchant-portal/src/x.tsx"],
        "auto",
        "selected",
        ["website", "merchant"],
        False,
        "partial",
    ),
    ([".github/workflows/deploy.yml"], "auto", "full", list(IMAGE_ORDER), True, "full"),
    (["apps/admin/x.tsx", "apps/merchant-portal/y.tsx", "apps/driver-portal/z.tsx", "apps/customer/w.tsx"], "auto", "portals", ["admin", "merchant", "driver", "customer"], False, "partial"),
)


def fail(msg: str, failures: list[str]) -> None:
    failures.append(msg)


def main() -> int:
    failures: list[str] = []
    rules = load_rules(RULES_PATH)

    for image_id, spec in rules["images"].items():
        dockerfile = ROOT / spec["dockerfile"]
        if not dockerfile.is_file():
            fail(f"missing dockerfile for {image_id}: {spec['dockerfile']}", failures)
        if image_id not in IMAGE_ORDER:
            fail(f"image {image_id} not in IMAGE_ORDER", failures)

    for scope, spec in rules["scopes"].items():
        if spec.get("kind") == "named":
            for image_id in spec.get("images") or []:
                if image_id not in rules["images"]:
                    fail(f"scope {scope} references unknown image {image_id}", failures)

    for files, requested, scope, images, migrate, rollout in GOLDEN:
        plan = build_plan(rules, requested=requested, files=files)
        if plan["scope"] != scope:
            fail(f"{files!r} scope={plan['scope']!r} want {scope!r}", failures)
        if plan["images"] != images:
            fail(f"{files!r} images={plan['images']!r} want {images!r}", failures)
        if plan["migrate"] != migrate:
            fail(f"{files!r} migrate={plan['migrate']!r} want {migrate!r}", failures)
        if plan["rollout"] != rollout:
            fail(f"{files!r} rollout={plan['rollout']!r} want {rollout!r}", failures)

    deploy = DEPLOY_YML.read_text(encoding="utf-8")
    for needle in (
        "scripts/resolve_deploy_plan.py",
        'echo "::error::DOPPLER_TOKEN is required',
        "sync-secrets.sh",
        "strategy:",
        "matrix:",
        "cid-",
        "portals",
    ):
        if needle not in deploy:
            fail(f"deploy.yml missing required token: {needle}", failures)

    options = (
        subprocess.check_output(
            ["python3", "-c", "import json,re,pathlib; t=pathlib.Path('.github/workflows/deploy.yml').read_text(); print('ok')"],
            cwd=ROOT,
        )
        .decode()
        .strip()
    )
    if options != "ok":
        fail("deploy.yml unreadable", failures)

    for scope in rules["scopes"]:
        if scope == "selected":
            continue
        if f"- {scope}" not in deploy and scope not in ("none",):
            # none is not a dispatch option; auto/full/portals/apps must be
            if scope in ("auto", "full", "portals", "api", "website", "merchant", "admin", "driver", "customer"):
                fail(f"deploy.yml dispatch options missing {scope}", failures)

    print("Deploy plan guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print(f"  OK — {len(GOLDEN)} golden cases, {len(rules['images'])} images, rules={RULES_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
