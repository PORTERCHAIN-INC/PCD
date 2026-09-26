#!/usr/bin/env python3
"""Blog CMS handshake — one content owner, public read, no file catalog."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    ("model", ROOT / "apps/api/src/porterchain_api/website_content_models.py"),
    ("service", ROOT / "apps/api/src/porterchain_api/content_engine/blog_service.py"),
    ("admin router", ROOT / "apps/api/src/porterchain_api/routers/admin/blog.py"),
    ("public router", ROOT / "apps/api/src/porterchain_api/routers/public_blog.py"),
    ("migration", ROOT / "apps/api/alembic/versions/t3u4v5w6x7y8_blog_posts.py"),
    ("admin lib", ROOT / "apps/admin/src/lib/blog.ts"),
    ("shared types", ROOT / "packages/types/src/blog.ts"),
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
    if "Lead Workspace" not in nav:
        failures.append("admin-nav.ts missing Lead Workspace")
    # Source constants remain for deep-link chips / isNavActive even after Growth collapse.
    if "website_driver_partner" not in nav:
        failures.append("admin-nav.ts missing driver partner lead source constant")
    if "website_contact" not in nav:
        failures.append("admin-nav.ts missing website_contact lead source constant")
    if "website_newsletter" not in nav:
        failures.append("admin-nav.ts missing website_newsletter lead source constant")

    revalidate_route = ROOT / "website/src/app/api/revalidate/blog/route.ts"
    if not revalidate_route.is_file():
        failures.append("missing website /api/revalidate/blog route")
    else:
        rev = revalidate_route.read_text(encoding="utf-8")
        if "revalidateTag" not in rev or "WEBSITE_REVALIDATE_SECRET" not in rev:
            failures.append("revalidate/blog route missing revalidateTag or secret")
    revalidate_py = ROOT / "apps/api/src/porterchain_api/content_engine/blog_revalidate.py"
    if not revalidate_py.is_file():
        failures.append("missing content_engine/blog_revalidate.py")
    admin_blog = (ROOT / "apps/api/src/porterchain_api/routers/admin/blog.py").read_text(
        encoding="utf-8"
    )
    if "notify_blog_revalidate" not in admin_blog:
        failures.append("admin blog router must call notify_blog_revalidate")

    form = (ROOT / "apps/admin/src/components/blog/BlogPostForm.tsx").read_text(encoding="utf-8")
    for marker in (
        "Upload cover",
        "Insert image in body",
        "cover_image_url",
        "Publish checklist",
        "Preview",
    ):
        if marker not in form:
            failures.append(f"BlogPostForm missing {marker}")
    lib = (ROOT / "apps/admin/src/lib/blog.ts").read_text(encoding="utf-8")
    if "uploadMedia" not in lib:
        failures.append("admin lib/blog.ts missing uploadMedia")
    if "cover_image_url" not in lib:
        failures.append("admin lib/blog.ts missing cover_image_url")
    media_py = (ROOT / "apps/api/src/porterchain_api/content_engine/blog_media.py").read_text(
        encoding="utf-8"
    )
    if "blog_media_public_base" not in media_py:
        failures.append("blog_media.py missing CDN public base helper")
    media_s3 = ROOT / "apps/api/src/porterchain_api/content_engine/blog_media_s3.py"
    if not media_s3.is_file():
        failures.append("missing blog_media_s3.py optional R2/S3 uploader")
    elif "put_blog_media_object" not in media_s3.read_text(encoding="utf-8"):
        failures.append("blog_media_s3.py missing put_blog_media_object")
    if "put_blog_media_object" not in media_py:
        failures.append("blog_media.save_blog_image must call S3 mirror helper")

    media = ROOT / "apps/api/src/porterchain_api/content_engine/blog_media.py"
    if not media.is_file():
        failures.append("missing blog_media.py")
    cover_mig = ROOT / "apps/api/alembic/versions/u4v5w6x7y8z9_blog_cover_image.py"
    if not cover_mig.is_file():
        failures.append("missing cover_image migration u4v5w6x7y8z9")
    pub = (ROOT / "apps/api/src/porterchain_api/routers/public_blog.py").read_text(encoding="utf-8")
    if "media/{filename}" not in pub:
        failures.append("public blog missing media route")

    blog_ts = (ROOT / "website/src/lib/blog.ts").read_text(encoding="utf-8")
    if "getBlogMediaBase" not in blog_ts and "NEXT_PUBLIC_BLOG_MEDIA_CDN" not in blog_ts:
        failures.append("website blog.ts missing CDN media base")
    if "/v1/public/blog/posts" not in blog_ts:
        failures.append("website blog.ts missing public API fetch")
    if "content/blog" in blog_ts or "getAllPostSlugsSync" in blog_ts:
        failures.append("website blog.ts still reads the markdown catalog")
    if "blog_catalog_truncated" not in blog_ts:
        failures.append("website blog.ts missing truncation tripwire")
    if "`blog:${locale}`" not in blog_ts and 'tags: ["blog"' not in blog_ts:
        failures.append("website blog.ts missing cache tags")
    if "case_study" not in blog_ts or "featured" not in blog_ts:
        failures.append("website blog.ts missing public list filter opts")
    playbook = ROOT / "docs/WEBSITE_PAGE_PLAYBOOK.md"
    if not playbook.is_file():
        failures.append("missing docs/WEBSITE_PAGE_PLAYBOOK.md")
    service = (ROOT / "apps/api/src/porterchain_api/content_engine/blog_service.py").read_text(
        encoding="utf-8"
    )
    if "reading_minutes_for" not in service:
        failures.append("BlogService missing reading_minutes_for")
    if "offset" not in service or "case_study" not in service:
        failures.append("BlogService list_posts missing offset/case_study filters")
    pub = (ROOT / "apps/api/src/porterchain_api/routers/public_blog.py").read_text(encoding="utf-8")
    if "offset" not in pub or "case_study" not in pub:
        failures.append("public_blog list missing offset/case_study query params")
    blog_meta = (ROOT / "website/src/lib/blog-meta.ts").read_text(encoding="utf-8")
    if 'source?: "api" | "file"' in blog_meta:
        failures.append("website blog-meta.ts still has the file merge marker")
    if "resolveBlogCover" not in blog_meta:
        failures.append("website blog-meta.ts missing resolveBlogCover")
    if "server-only" not in blog_ts:
        failures.append("website blog.ts must be server-only")

    sitemap = (ROOT / "website/src/lib/seo/sitemap-entries.ts").read_text(encoding="utf-8")
    if "getAllPostSlugsSync" in sitemap or "content/blog" in sitemap:
        failures.append("sitemap still unions file slugs")

    content_engine = ROOT / "apps/api/src/porterchain_api/content_engine"
    for path in content_engine.glob("*.py"):
        if "admin_engine" in path.read_text(encoding="utf-8"):
            failures.append(f"{path.name} imports admin_engine")

    if "admin_engine" in pub:
        failures.append("public_blog.py imports admin_engine")
    if "serialize_public" not in pub:
        failures.append("public_blog.py must use serialize_public")
    if 'data.pop("created_by"' not in service:
        failures.append("serialize_public must drop created_by")

    mirror = (
        ROOT / "apps/api/src/porterchain_api/booking_engine/crm_lead_mirror.py"
    ).read_text(encoding="utf-8")
    if "CrmSalesService" in mirror or "create_lead" in mirror:
        failures.append("crm_lead_mirror still bypasses LeadIngestService")
    if "LeadIngestService" not in mirror:
        failures.append("crm_lead_mirror missing LeadIngestService")

    failures.extend(_closed_set_drift(ROOT))
    failures.extend(_list_limit_drift(ROOT))

    for method in ("@router.post", "@router.patch", "@router.delete"):
        if method not in admin_blog:
            failures.append(f"admin blog router missing {method}")

    business_hero = (
        ROOT / "website/src/components/marketing/business/sections/BusinessHero.tsx"
    ).read_text(encoding="utf-8")
    # Regression: deleted MerchantSsoButtons must not return on BusinessHero
    if "MerchantSsoButtons" in business_hero:
        failures.append("BusinessHero must not reintroduce MerchantSsoButtons — quote page only")

    print("Blog CMS guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: content owner, public API, website reader, lead ingest")
    return 0


def _quoted(block: str) -> list[str]:
    return re.findall(r'"([^"]+)"', block)


def _py_set(text: str, name: str) -> list[str]:
    match = re.search(rf"{name} = frozenset\(\s*\{{(.*?)\}}\s*\)", text, re.S)
    if not match:
        return []
    return _quoted(match.group(1))


def _ts_array(text: str, name: str) -> list[str]:
    match = re.search(rf"(?:export )?const {name} = \[(.*?)\] as const", text, re.S)
    if not match:
        return []
    return _quoted(match.group(1))


def _closed_set_drift(root: Path) -> list[str]:
    service = (root / "apps/api/src/porterchain_api/content_engine/blog_service.py").read_text(
        encoding="utf-8"
    )
    shared = (root / "packages/types/src/blog.ts").read_text(encoding="utf-8")
    admin = (root / "apps/admin/src/lib/blog.ts").read_text(encoding="utf-8")
    website = (root / "website/src/data/blog-categories.ts").read_text(encoding="utf-8")
    routing = (root / "website/src/i18n/routing.ts").read_text(encoding="utf-8")
    failures: list[str] = []
    py_categories = _py_set(service, "BLOG_CATEGORIES")
    shared_categories = _ts_array(shared, "BLOG_CATEGORIES")
    if py_categories != shared_categories:
        failures.append("packages/types BLOG_CATEGORIES drifted from BlogService")
    if '@porterchain/types' not in admin or "BLOG_CATEGORIES" not in admin:
        failures.append("admin lib/blog.ts must re-export BLOG_CATEGORIES from @porterchain/types")
    if '@porterchain/types' not in website or "BLOG_CATEGORIES" not in website:
        failures.append(
            "website blog-categories.ts must re-export BLOG_CATEGORIES from @porterchain/types"
        )
    py_locales = _py_set(service, "BLOG_LOCALES")
    if py_locales != _ts_array(shared, "BLOG_LOCALES"):
        failures.append("packages/types BLOG_LOCALES drifted from BlogService")
    if '@porterchain/types' not in admin or "BLOG_LOCALES" not in admin:
        failures.append("admin lib/blog.ts must re-export BLOG_LOCALES from @porterchain/types")
    route_match = re.search(r"locales:\s*\[(.*?)\]", routing, re.S)
    route_locales = _quoted(route_match.group(1)) if route_match else []
    if py_locales != route_locales:
        failures.append("website routing locales drifted from BlogService")
    if _py_set(service, "BLOG_STATUSES") != _ts_array(shared, "BLOG_STATUSES"):
        failures.append("packages/types BLOG_STATUSES drifted from BlogService")
    if '@porterchain/types' not in admin or "BLOG_STATUSES" not in admin:
        failures.append("admin lib/blog.ts must re-export BLOG_STATUSES from @porterchain/types")
    website_loader = (root / "website/src/lib/blog.ts").read_text(encoding="utf-8")
    if "ApiBlogRow" in website_loader:
        failures.append("website lib/blog.ts must not define ApiBlogRow — use @porterchain/types")
    if '@porterchain/types' not in website_loader or "publicBlogPostMetaSchema" not in website_loader:
        failures.append(
            "website lib/blog.ts must parse public blog rows via @porterchain/types schemas"
        )
    if "BLOG_PAGE_SIZE" not in website_loader:
        failures.append("website lib/blog.ts must define BLOG_PAGE_SIZE for paged catalog fetches")
    if "getPreviewPost" not in website_loader:
        failures.append("website lib/blog.ts must expose getPreviewPost for draft preview")
    preview_page = ROOT / "website/src/app/[locale]/blog/preview/[slug]/page.tsx"
    if not preview_page.is_file():
        failures.append("missing website blog preview route")
    public_blog = (ROOT / "apps/api/src/porterchain_api/routers/public_blog.py").read_text(
        encoding="utf-8"
    )
    if "/preview" not in public_blog or "verify_blog_preview_token" not in public_blog:
        failures.append("public_blog missing signed preview endpoint")
    admin_blog = (ROOT / "apps/api/src/porterchain_api/routers/admin/blog.py").read_text(
        encoding="utf-8"
    )
    if "preview-url" not in admin_blog or "make_blog_preview_token" not in admin_blog:
        failures.append("admin blog missing preview-url endpoint")
    authors = (ROOT / "website/src/data/blog-authors.ts").read_text(encoding="utf-8")
    if '@porterchain/types' not in authors or "getBlogAuthor" not in authors:
        failures.append("website blog-authors must re-export from @porterchain/types")
    ownership = ROOT / "website/src/lib/seo/OWNERSHIP.ts"
    if not ownership.is_file():
        failures.append("missing website/src/lib/seo/OWNERSHIP.ts dual-tree lock")
    return failures


def _list_limit_drift(root: Path) -> list[str]:
    pagination = (root / "apps/api/src/porterchain_api/platform/pagination.py").read_text(
        encoding="utf-8"
    )
    website = (root / "website/src/lib/blog.ts").read_text(encoding="utf-8")
    admin = (root / "apps/admin/src/lib/blog.ts").read_text(encoding="utf-8")
    cap = re.search(r"MAX_LIST_LIMIT = (\d+)", pagination)
    site = re.search(r"BLOG_LIST_LIMIT = (\d+)", website)
    failures: list[str] = []
    if not cap or not site or cap.group(1) != site.group(1):
        failures.append("website BLOG_LIST_LIMIT != MAX_LIST_LIMIT")
    if not cap or f'params.set("limit", "{cap.group(1)}")' not in admin:
        failures.append("admin blog list limit != MAX_LIST_LIMIT")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
