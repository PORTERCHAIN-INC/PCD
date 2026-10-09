#!/usr/bin/env python3
"""Sitemap contract check against a running website build (read-only GETs).

Every <loc> in /sitemap.xml (and its child sitemaps) must:
  * return 200 with no redirect,
  * not be noindex (meta robots or X-Robots-Tag),
  * carry a self-referencing canonical,
  * list itself in its hreflang set, plus x-default, with every alternate also in the sitemap.
Also asserts the sitemap holds no ?from= URLs, /ca/ paths or doubled locales.

Usage:
  cd website && pnpm build && npx next start -p 3100 &
  python3 scripts/verify_sitemap_indexable.py http://localhost:3100
Sitemap <loc>s use the configured site URL (prod domain or localhost:3000); their host is
mapped onto BASE so a local build can be verified.
"""
from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit, urlunsplit

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3100").rstrip("/")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):  # noqa: ANN002, ANN003
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def to_base(url: str) -> str:
    b, u = urlsplit(BASE), urlsplit(url)
    return urlunsplit((b.scheme, b.netloc, u.path, u.query, ""))


def get(url: str) -> tuple[int, dict[str, str], str]:
    req = urllib.request.Request(url, headers={"User-Agent": "PorterchainSitemapVerify/1.0"})
    try:
        with OPENER.open(req, timeout=60) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, ""


def locs(xml: str) -> list[str]:
    return [l.replace("&amp;", "&") for l in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)]


def path_of(url: str) -> str:
    return urlsplit(url).path.rstrip("/") or "/"


def attr(tag: str, name: str) -> str:
    m = re.search(rf'{name}="([^"]*)"', tag, re.I)
    return m.group(1) if m else ""


def check(url: str, sitemap_paths: set[str]) -> list[str]:
    status, headers, body = get(to_base(url))
    p = path_of(url)
    errs: list[str] = []
    if status != 200:
        return [f"{p}: HTTP {status} {headers.get('location', '')}".strip()]
    if "noindex" in headers.get("x-robots-tag", "").lower():
        errs.append(f"{p}: X-Robots-Tag noindex")
    for tag in re.findall(r"<meta[^>]+>", body, re.I):
        if attr(tag, "name").lower() == "robots" and "noindex" in attr(tag, "content").lower():
            errs.append(f"{p}: meta robots noindex")
    links = re.findall(r"<link[^>]+>", body, re.I)
    canon = [attr(t, "href") for t in links if attr(t, "rel").lower() == "canonical"]
    if len(canon) != 1 or path_of(canon[0]) != p:
        errs.append(f"{p}: canonical {canon}")
    alts = {attr(t, "hreflang"): attr(t, "href") for t in links if attr(t, "hreflang")}
    if alts:
        if "x-default" not in alts:
            errs.append(f"{p}: hreflang without x-default")
        if p not in {path_of(h) for h in alts.values()}:
            errs.append(f"{p}: hreflang set does not include itself")
        for lang, href in alts.items():
            if path_of(href) not in sitemap_paths:
                errs.append(f"{p}: hreflang {lang} → {path_of(href)} not in sitemap")
    return errs


def main() -> int:
    status, _, index = get(BASE + "/sitemap.xml")
    if status != 200:
        print(f"FAIL: /sitemap.xml HTTP {status}")
        return 1
    children = locs(index)
    urls: list[str] = []
    errors: list[str] = []
    for child in children:
        s, _, xml = get(to_base(child))
        if s != 200:
            errors.append(f"child sitemap {child}: HTTP {s}")
            continue
        urls += locs(xml)
    seen: set[str] = set()
    for u in urls:
        p = path_of(u)
        if p in seen:
            errors.append(f"{p}: duplicate sitemap entry")
        seen.add(p)
        if "from=" in u or re.match(r"^/ca(/|$)", p) or re.match(r"^/(en|fr)/(en|fr)(/|$)", p):
            errors.append(f"{u}: legacy/param URL in sitemap")
    with ThreadPoolExecutor(8) as ex:
        for errs in ex.map(lambda u: check(u, seen), urls):
            errors += errs
    print(f"sitemaps={len(children)} urls={len(urls)} errors={len(errors)}")
    for e in errors[:50]:
        print("  -", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
