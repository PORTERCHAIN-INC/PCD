#!/usr/bin/env python3
"""Blog CMS guard — admin CRUD + public read API + website merge."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    ("model", ROOT / "apps/api/src/porterchain_api/website_content_models.py"),
    ("service", ROOT / "apps/api/src/porterchain_api/admin_engine/blog_service.py"),
    ("admin router", ROOT / "apps/api/src/porterchain_api/routers/admin/blog.py"),
    ("public router", ROOT / "apps/api/src/porterchain_api/routers/public_blog.py"),
    ("migration", ROOT / "apps/api/alembic/versions/t3u4v5w6x7y8_blog_posts.py"),
    ("admin lib", ROOT / "apps/admin/src/lib/blog.ts"),
    ("admin list", ROOT / "apps/admin/src/app/(ops)/blog/page.tsx"),
    ("admin new", ROOT / "apps/admin/src/app/(ops)/blog/new/page.tsx"),
    ("admin edit", ROOT / "apps/admin/src/app/(ops)/blog/[id]/page.tsx"),
    ("admin form", ROOT / "apps/admin/src/components/blog/BlogPostForm.tsx"),
    ("website loader", ROOT / "website/src/lib/blog.ts"),
    ("import script", ROOT / "scripts/import_blog_markdown.py"),
]


def main() -> int:
    failures: list[str] = []

    for label, path in REQUIRED:
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    rbac = (ROOT / "apps/api/src/porterchain_api/admin_engine/rbac.py").read_text(encoding="utf-8")
    if '"content"' not in rbac or '"content_read"' not in rbac:
        failures.append("rbac.py missing content/content_read modules")

    admin_init = (ROOT / "apps/api/src/porterchain_api/routers/admin/__init__.py").read_text(encoding="utf-8")
    if "blog" not in admin_init:
        failures.append("routers/admin/__init__.py missing blog import")

    main_py = (ROOT / "apps/api/src/porterchain_api/main.py").read_text(encoding="utf-8")
    if "public_blog.router" not in main_py:
        failures.append("main.py missing public_blog router")

    nav = (ROOT / "apps/admin/src/lib/admin-nav.ts").read_text(encoding="utf-8")
    if 'href: "/blog"' not in nav:
        failures.append("admin-nav.ts missing /blog link")
    if 'label: "Blog"' not in nav and 'label: "Website Blog"' not in nav:
        failures.append("admin-nav.ts missing Blog label")
    if "Merchant Leads" not in nav:
        failures.append("admin-nav.ts missing Merchant Leads")
    if "Driver Leads" not in nav and "Driver Applications" not in nav:
        failures.append("admin-nav.ts missing Driver Leads / Driver Applications")
    if "website_driver_partner" not in nav:
        failures.append("admin-nav.ts missing driver partner lead source href")

    form = (ROOT / "apps/admin/src/components/blog/BlogPostForm.tsx").read_text(encoding="utf-8")
    for marker in ("Upload cover", "Insert image in body", "cover_image_url"):
        if marker not in form:
            failures.append(f"BlogPostForm missing {marker}")
    lib = (ROOT / "apps/admin/src/lib/blog.ts").read_text(encoding="utf-8")
    if "uploadMedia" not in lib:
        failures.append("admin lib/blog.ts missing uploadMedia")
    if "cover_image_url" not in lib:
        failures.append("admin lib/blog.ts missing cover_image_url")

    media = ROOT / "apps/api/src/porterchain_api/admin_engine/blog_media.py"
    if not media.is_file():
        failures.append("missing blog_media.py")
    cover_mig = ROOT / "apps/api/alembic/versions/u4v5w6x7y8z9_blog_cover_image.py"
    if not cover_mig.is_file():
        failures.append("missing cover_image migration u4v5w6x7y8z9")
    pub = (ROOT / "apps/api/src/porterchain_api/routers/public_blog.py").read_text(encoding="utf-8")
    if "media/{filename}" not in pub:
        failures.append("public blog missing media route")

    blog_ts = (ROOT / "website/src/lib/blog.ts").read_text(encoding="utf-8")
    if "/v1/public/blog/posts" not in blog_ts:
        failures.append("website blog.ts missing public API fetch")
    blog_meta = (ROOT / "website/src/lib/blog-meta.ts").read_text(encoding="utf-8")
    if 'source?: "api" | "file"' not in blog_meta:
        failures.append("website blog-meta.ts missing api/file merge marker")
    if "resolveBlogCover" not in blog_meta:
        failures.append("website blog-meta.ts missing resolveBlogCover")
    if "server-only" not in blog_ts:
        failures.append("website blog.ts must be server-only (fs loaders)")

    admin_blog = (ROOT / "apps/api/src/porterchain_api/routers/admin/blog.py").read_text(encoding="utf-8")
    for method in ("@router.post", "@router.patch", "@router.delete"):
        if method not in admin_blog:
            failures.append(f"admin blog router missing {method}")

    business_hero = (
        ROOT / "website/src/components/business/sections/BusinessHero.tsx"
    ).read_text(encoding="utf-8")
    # Regression: deleted MerchantSsoButtons must not return on BusinessHero
    if "MerchantSsoButtons" in business_hero:
        failures.append("BusinessHero must not reintroduce MerchantSsoButtons — quote page only")

    print("Blog CMS guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: admin CRUD, public API, website merge, nav wired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
