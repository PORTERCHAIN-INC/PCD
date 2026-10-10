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
  ["/en/campaigns", "/en/delivery"],
  // FAQ consolidation (Oct 2026).
  ["/en/faq/delivery-pricing", "/en/delivery-cost-calculator"],
  ["/en/faq/pharmacy-delivery", "/en/delivery/pharmacy"],
  ["/en/faq/onboarding", "/en/faq"],
  ["/en/faq/some-unknown-cluster", "/en/faq"],
  // Industry merges (Oct 2026).
  ["/en/delivery/labs", "/en/delivery/pharmacy"],
  ["/en/delivery/labs/mississauga", "/en/delivery/pharmacy/mississauga"],
  ["/en/delivery/plumbing-electrical", "/en/delivery/construction"],
  ["/en/delivery/plumbing-electrical/vaughan", "/en/delivery/construction/vaughan"],
  ["/en/delivery/wholesale-traders", "/en/delivery/warehouses"],
  ["/en/delivery/wholesale-traders/brampton", "/en/delivery/warehouses/brampton"],
  // Footer consolidation (Oct 2026): merged pages → one 301 to the surviving page.
  ["/en/capabilities", "/en/platform"],
  ["/en/capabilities/multi-stop-delivery", "/en/platform"],
  ["/en/capabilities/exception-recovery", "/en/guides/delivery-failure-modes-and-recovery"],
  ["/fr/capabilities/inventory-transfers", "/fr/guides/inventory-transfers-between-locations"],
  ["/en/integrations-education/sms-status-notifications", "/en/integrations"],
  ["/en/integrations-education/webhooks-delivery-events", "/en/developers"],
  ["/en/solutions", "/en/delivery"],
  ["/en/solutions/medical", "/en/delivery/pharmacy"],
  ["/en/solutions/wholesale", "/en/delivery/warehouses"],
  ["/en/solutions/3pl", "/en/delivery/warehouses"],
  ["/en/solutions/fleet-overflow", "/en/business"],
  ["/fr/solutions/medical", "/en/delivery/pharmacy"],
  ["/en/construction", "/en/delivery/construction"],
  ["/en/how-porterchain-works", "/en/platform"],
  ["/how-it-works", "/en/platform"],
  ["/industries", "/en/delivery"],
  ["/ca/en/solutions/construction", "/en/delivery/construction"],
  // Legacy furniture URLs → the furniture industry hub (single hop).
  ["/industries/furniture-delivery", "/en/delivery/furniture"],
  ["/ca/en/industries/furniture-delivery", "/en/delivery/furniture"],
  ["/en/industries/furniture-delivery", "/en/delivery/furniture"],
  ["/fr/industries/furniture-delivery", "/en/delivery/furniture"],
  ["/en/industry/furniture", "/en/delivery/furniture"],
  ["/en/solutions/furniture", "/en/delivery/furniture"],
  ["/en/campaigns/furniture-delivery", "/en/delivery/furniture"],
  ["/en/toronto/furniture-delivery", "/en/delivery/furniture"],
  ["/en/delivery/furniture-delivery/mississauga", "/en/delivery/furniture/mississauga"],
  ["/en/delivery/furniture/milton", "/en/delivery/furniture"],
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

test("signed track/manage links keep their token through the locale redirect", () => {
  for (const [src, want] of [
    ["/track/PC-1/manage", "/en/track/PC-1/manage?t=abc.def"],
    ["/track/PC-1", "/en/track/PC-1?t=abc.def"],
  ]) {
    const res = resolveUrlPolicy(src, "?t=abc.def&from=x");
    assert.equal(res.action, "redirect");
    assert.equal((res as { location: string }).location, want);
  }
  const book = resolveUrlPolicy("/book", "?quote_id=q1&again=a1");
  assert.equal((book as { location: string }).location, "/en/book?quote_id=q1&again=a1");
});
