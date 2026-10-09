// Run: cd website && pnpm test:seo   (tsx --test src/lib/seo/url-policy.test.mts)
//
// Contract for every public URL (GSC "Page with redirect" / "Not found" clean-up, Oct 2026):
//   • a URL either passes, 410s, 404s, or 301s ONCE to a URL that itself passes (no chains/loops);
//   • redirect targets never carry ?from=, /ca/ or doubled locales;
//   • every sitemap (manifest) path passes untouched.
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { LOCALE_APP_SECTIONS, resolveUrlPolicy } from "./url-policy";
import { WEBSITE_REDIRECTS } from "./redirects";

const here = dirname(fileURLToPath(import.meta.url));
const manifest: string[] = JSON.parse(
  readFileSync(join(here, "../../generated/indexable-paths.json"), "utf8")
);
const legacy = readFileSync(join(here, "__fixtures__/legacy-paths.txt"), "utf8")
  .split("\n")
  .map((l) => l.trim())
  .filter((l) => l && !l.startsWith("#"));

function split(url: string): [string, string] {
  const i = url.indexOf("?");
  return i < 0 ? [url, ""] : [url.slice(0, i), url.slice(i)];
}

function assertFinal(from: string, location: string) {
  const [p, q] = split(location.split("#")[0]!);
  assert.ok(!/[?&]from=/.test(location), `${from} → ${location} keeps ?from=`);
  assert.ok(!/^\/ca(\/|$)/.test(p), `${from} → ${location} keeps /ca/`);
  assert.ok(
    !/^\/(en|fr)\/(en|fr|fr-ca|en-ca)(\/|$)/.test(p),
    `${from} → ${location} doubled locale`
  );
  const next = resolveUrlPolicy(p, q);
  assert.equal(next.action, "pass", `${from} → ${location} is a chain (${JSON.stringify(next)})`);
}

test("every sitemap path passes untouched", () => {
  assert.ok(manifest.length > 500);
  for (const p of manifest) assert.deepEqual(resolveUrlPolicy(p), { action: "pass" }, p);
});

test("every legacy / Search Console URL resolves in at most one hop", () => {
  assert.ok(legacy.length > 1000);
  const tally: Record<string, number> = {};
  for (const url of legacy) {
    const [p, q] = split(url);
    const r = resolveUrlPolicy(p, q);
    tally[r.action] = (tally[r.action] ?? 0) + 1;
    if (r.action === "redirect") assertFinal(url, r.location);
  }
  // Most of the legacy URL space must be recovered by a 301, not dropped.
  assert.ok((tally.redirect ?? 0) > (tally.gone ?? 0) * 10, JSON.stringify(tally));
});

test("registry destinations are final (no redirect chains / loops)", () => {
  for (const r of WEBSITE_REDIRECTS) {
    const src = r.source.replace(/:(\w+)\*?/g, (_m, n) =>
      n === "locale" ? "en" : n === "city" ? "toronto" : "x"
    );
    for (const prefix of src.startsWith("/") ? [""] : ["/en/", "/fr/"]) {
      const res = resolveUrlPolicy(prefix + src);
      if (res.action === "redirect") assertFinal(prefix + src, res.location);
    }
  }
});

test("LOCALE_APP_SECTIONS mirrors app/[locale] route folders", () => {
  const dir = join(here, "../../app/[locale]");
  const folders = readdirSync(dir).filter(
    (n) => statSync(join(dir, n)).isDirectory() && !n.startsWith("[") && !n.startsWith("(")
  );
  assert.deepEqual([...folders].sort(), [...LOCALE_APP_SECTIONS].sort());
});

const EXPECTED: Array<[string, string | "gone"]> = [
  ["/ca/fr-ca/delivery/chocolate/mississauga", "/fr/industry/chocolate"],
  ["/en/blog/wholesale-distribution-gta", "pass"],
  ["/en/blog/same-day-b2b-delivery-toronto", "pass"],
  ["/fr/fr/sign-up?from=x/y&intent=quote", "/fr/sign-up?intent=quote"],
  ["/ca/en/resources/logistics-for-coffee-roasters", "/en/blog/coffee-supply-chain-freshness"],
  ["/ca/en", "/en"],
  ["/en/en/business", "/en/business"],
  ["/about", "/en/company"],
  ["/standards", "/en/trust"],
  ["/en/brampton/medium-truck", "/en/brampton/box-truck-delivery"],
  ["/en/london/sedan-delivery", "redirect"],
  ["/en/campaigns", "/en/solutions"],
  ["/api-integrations", "/en/integrations"],
  ["/index.html", "/en"],
  ["/blog/rss.xml", "pass"],
  ["/openapi.json", "/en/developers"],
];

test("Search Console examples map to the agreed destinations", () => {
  for (const [from, want] of EXPECTED) {
    const [p, q] = split(from);
    const r = resolveUrlPolicy(p, q);
    if (want === "pass") assert.equal(r.action, "pass", from);
    else if (want === "gone") assert.equal(r.action, "gone", from);
    else if (want === "redirect") assert.equal(r.action, "redirect", from);
    else {
      assert.equal(r.action, "redirect", `${from}: ${JSON.stringify(r)}`);
      if (r.action === "redirect") assert.equal(r.location, want, from);
    }
  }
});
