#!/usr/bin/env python3
"""Resolve a deploy plan from infrastructure/deploy/deploy-rules.json.

SSOT is the JSON file. This script does not invent scopes or images.
CI and Deploy must call this; do not copy the glob list into YAML.

Usage:
  python3 scripts/resolve_deploy_plan.py --changed-files paths.txt
  python3 scripts/resolve_deploy_plan.py --scope merchant
  git diff --name-only HEAD^ HEAD | python3 scripts/resolve_deploy_plan.py
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "infrastructure/deploy/deploy-rules.json"
IMAGE_ORDER = ("api", "website", "admin", "merchant", "driver", "customer")


def load_rules(path: Path = RULES_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if int(data.get("version") or 0) != 1:
        raise SystemExit(f"unsupported deploy-rules version: {data.get('version')}")
    return data


def normalize_path(raw: str) -> str:
    return raw.strip().replace("\\", "/").lstrip("./")


def glob_match(path: str, pattern: str) -> bool:
    path = normalize_path(path)
    pattern = pattern.replace("\\", "/")
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(prefix + "/")
    if "*" in pattern or "?" in pattern:
        return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path.split("/")[-1], pattern)
    return path == pattern or path.startswith(pattern + "/")


def any_match(path: str, patterns: list[str]) -> bool:
    return any(glob_match(path, p) for p in patterns)


def classify_files(rules: dict[str, Any], files: list[str]) -> tuple[set[str], bool, bool]:
    """Return (image_ids, force_full, only_ignored_or_empty)."""
    force_full = False
    marked: set[str] = set()
    leftover = False
    images: dict[str, Any] = rules["images"]
    force_globs = list(rules.get("force_full_globs") or [])
    ignore_globs = list(rules.get("ignore_globs") or [])

    cleaned = [normalize_path(f) for f in files if normalize_path(f)]
    if not cleaned:
        return set(), True, False

    for path in cleaned:
        if any_match(path, force_globs):
            force_full = True
            continue
        if any_match(path, ignore_globs):
            continue
        hit = False
        for image_id, spec in images.items():
            if any_match(path, list(spec.get("input_globs") or [])):
                marked.add(image_id)
                hit = True
        if not hit:
            leftover = True

    if leftover:
        force_full = True
    return marked, force_full, (not marked and not force_full)


def named_scope_images(rules: dict[str, Any], scope: str) -> list[str]:
    spec = (rules.get("scopes") or {}).get(scope)
    if not spec or spec.get("kind") != "named":
        raise SystemExit(f"unknown deploy scope: {scope}")
    return list(spec.get("images") or [])


def auto_scope_name(rules: dict[str, Any], image_ids: list[str]) -> str:
    if not image_ids:
        return "none"
    flavors = {rules["images"][i]["flavor"] for i in image_ids}
    if set(image_ids) == set(named_scope_images(rules, "full")):
        return "full"
    if set(image_ids) == set(named_scope_images(rules, "portals")):
        return "portals"
    if len(image_ids) == 1:
        return image_ids[0]
    if flavors <= {"portal"}:
        return "portals"
    return "selected"


def ordered_images(image_ids: set[str] | list[str]) -> list[str]:
    wanted = set(image_ids)
    return [i for i in IMAGE_ORDER if i in wanted]


def content_id_for_image(rules: dict[str, Any], image_id: str, *, root: Path = ROOT) -> str:
    spec = rules["images"][image_id]
    globs = list(spec.get("input_globs") or [])
    dockerfile = spec["dockerfile"]
    pathspecs = [*globs, dockerfile]
    try:
        listing = subprocess.check_output(
            ["git", "ls-files", "-s", "--", *pathspecs],
            cwd=root,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        listing = b""
    digest = hashlib.sha256()
    digest.update(image_id.encode())
    digest.update(b"\n")
    digest.update(listing)
    return digest.hexdigest()[:16]


def build_plan(
    rules: dict[str, Any],
    *,
    requested: str,
    files: list[str],
    with_content_ids: bool = False,
) -> dict[str, Any]:
    requested = (requested or "auto").strip()
    scopes = rules["scopes"]
    if requested not in scopes:
        raise SystemExit(f"unknown deploy scope: {requested}")

    if requested != "auto":
        image_ids = ordered_images(named_scope_images(rules, requested))
        scope_name = requested
        force_full = requested == "full"
    else:
        marked, force_full, only_ignored = classify_files(rules, files)
        if force_full:
            image_ids = ordered_images(named_scope_images(rules, "full"))
            scope_name = "full"
        elif only_ignored:
            image_ids = []
            scope_name = "none"
        else:
            image_ids = ordered_images(marked)
            scope_name = auto_scope_name(rules, image_ids)

    if scope_name == "none" or not image_ids:
        rollout = "none"
        migrate = False
    elif scope_name == "full":
        rollout = "full"
        migrate = True
    else:
        rollout = "partial"
        migrate = any(rules["images"][i].get("migrate") for i in image_ids)

    registry = str(rules["registry"]).rstrip("/")
    images_out: list[dict[str, Any]] = []
    for image_id in image_ids:
        spec = rules["images"][image_id]
        row = {
            "id": image_id,
            "repository": spec["repository"],
            "dockerfile": spec["dockerfile"],
            "flavor": spec["flavor"],
            "image": f"{registry}/{spec['repository']}",
            "compose_services": list(spec["compose_services"]),
        }
        if with_content_ids:
            row["cid"] = content_id_for_image(rules, image_id)
        images_out.append(row)

    services: list[str] = []
    for row in images_out:
        for svc in row["compose_services"]:
            if svc not in services:
                services.append(svc)

    pins = {i: i in image_ids for i in IMAGE_ORDER}
    matrix = {"include": images_out} if images_out else {"include": [{"id": "_noop", "skip": True}]}

    return {
        "version": rules["version"],
        "requested": requested,
        "scope": scope_name,
        "rollout": rollout,
        "migrate": migrate,
        "skip": rollout == "none",
        "images": [row["id"] for row in images_out],
        "services": services,
        "pins": pins,
        "matrix": matrix,
        "build_count": len(images_out),
        "image_rows": images_out,
    }


def github_outputs(plan: dict[str, Any]) -> str:
    pins = plan["pins"]
    lines = [
        f"scope={plan['scope']}",
        f"rollout={plan['rollout']}",
        f"migrate={'true' if plan['migrate'] else 'false'}",
        f"skip={'true' if plan['skip'] else 'false'}",
        f"build_count={plan['build_count']}",
        f"services={','.join(plan['services'])}",
        f"pin_api={'true' if pins['api'] else 'false'}",
        f"pin_website={'true' if pins['website'] else 'false'}",
        f"pin_admin={'true' if pins['admin'] else 'false'}",
        f"pin_merchant={'true' if pins['merchant'] else 'false'}",
        f"pin_driver={'true' if pins['driver'] else 'false'}",
        f"pin_customer={'true' if pins['customer'] else 'false'}",
        f"matrix={json.dumps(plan['matrix'], separators=(',', ':'))}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", default="auto")
    parser.add_argument("--changed-files", help="File with one repo-relative path per line")
    parser.add_argument("--rules", default=str(RULES_PATH))
    parser.add_argument("--github-output", action="store_true")
    parser.add_argument("--content-ids", action="store_true")
    args = parser.parse_args()

    rules = load_rules(Path(args.rules))
    if args.changed_files:
        files = Path(args.changed_files).read_text(encoding="utf-8").splitlines()
    elif not sys.stdin.isatty():
        files = sys.stdin.read().splitlines()
    else:
        files = []

    plan = build_plan(rules, requested=args.scope, files=files, with_content_ids=args.content_ids)
    if args.github_output:
        print(github_outputs(plan), end="")
        return 0
    json.dump(plan, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
