// Run: cd website && node --test src/lib/seo/delivery-programmatic.test.mjs src/lib/marketing/calculator-lead.test.mjs
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import test from "node:test";

import {
  COVERAGE_FSA_COUNT,
  DELIVERY_AREAS,
  DELIVERY_VERTICALS,
  ENTITY_FACTS,
  buildDeliveryBreadcrumbJsonLd,
  buildDeliveryFaqJsonLd,
  buildDeliveryPageContent,
  buildDeliveryServiceJsonLd,
  deliveryBreadcrumbs,
  getDeliveryArea,
  getDeliveryVertical,
  indexability,
  listDeliveryPages,
  nearbyAreas,
} from "./delivery-programmatic.ts";
import { GTA150_FSA_CODES } from "./gta150FsaCodes.ts";

const BASE = "https://porterchain.com";
const repo = new URL("../../../../", import.meta.url);

/** Minimal schema.org JSON-LD validator for the types these pages emit. */
function validateJsonLd(node, path = "$") {
  const errors = [];
  const req = (obj, key) => {
    if (obj[key] === undefined || obj[key] === null || obj[key] === "")
      errors.push(`${path}.${key} missing`);
  };
  if (path === "$") {
    if (node["@context"] !== "https://schema.org")
      errors.push("$.@context must be https://schema.org");
    if (JSON.stringify(node).includes("undefined")) errors.push("contains 'undefined'");
    JSON.parse(JSON.stringify(node));
  }
  const type = node["@type"];
  if (!type) errors.push(`${path}.@type missing`);
  switch (type) {
    case "Service":
      ["name", "serviceType", "provider", "areaServed", "url"].forEach((k) => req(node, k));
      if (node.offers) errors.push(...validateJsonLd(node.offers, `${path}.offers`));
      if (node.areaServed?.["@type"] === "Place") {
        const geo = node.areaServed.geo;
        if (!(geo && typeof geo.latitude === "number" && typeof geo.longitude === "number")) {
          errors.push(`${path}.areaServed.geo invalid`);
        }
      }
      break;
    case "Offer":
      if (node.priceCurrency !== "CAD") errors.push(`${path}.priceCurrency must be CAD`);
      if ("price" in node) errors.push(`${path}.price must not be invented`);
      if (!/^https:\/\//.test(node.url ?? "")) errors.push(`${path}.url must be absolute`);
      if (node.priceSpecification?.valueAddedTaxIncluded !== true) errors.push(`${path}.tax flag`);
      break;
    case "FAQPage":
      if (!Array.isArray(node.mainEntity) || !node.mainEntity.length)
        errors.push(`${path}.mainEntity empty`);
      for (const q of node.mainEntity ?? []) {
        if (q["@type"] !== "Question" || !q.name) errors.push(`${path} question invalid`);
        if (q.acceptedAnswer?.["@type"] !== "Answer" || !q.acceptedAnswer.text)
          errors.push(`${path} answer invalid`);
      }
      break;
    case "BreadcrumbList":
      (node.itemListElement ?? []).forEach((item, i) => {
        if (item["@type"] !== "ListItem" || item.position !== i + 1)
          errors.push(`${path} position ${i}`);
        if (!/^https:\/\//.test(item.item ?? "")) errors.push(`${path} item ${i} not absolute`);
      });
      if (!node.itemListElement?.length) errors.push(`${path}.itemListElement empty`);
      break;
    default:
      errors.push(`${path} unexpected @type ${type}`);
  }
  return errors;
}

test("only meaningful combinations are generated (88) and weak ones are noindex", () => {
  const pages = listDeliveryPages();
  assert.equal(DELIVERY_VERTICALS.length, 5);
  assert.equal(DELIVERY_AREAS.length, 18);
  assert.equal(pages.length, 88);
  assert.equal(new Set(pages.map((p) => p.path)).size, pages.length);
  const noindex = pages.filter((p) => !p.index);
  assert.equal(noindex.length, 8);
  assert.ok(noindex.every((p) => p.reason === "thin_coverage" || p.reason === "time_critical_far"));
  // Warehouses / wholesale only where there is industrial land.
  assert.ok(!pages.some((p) => p.vertical === "warehouses" && p.area === "downtown-toronto"));
  assert.ok(pages.some((p) => p.vertical === "warehouses" && p.area === "mississauga" && p.index));
  // Time-critical verticals far from the hub are rendered but not indexed.
  assert.deepEqual(indexability(getDeliveryVertical("pharmacy"), getDeliveryArea("hamilton")), {
    index: false,
    reason: "time_critical_far",
  });
  assert.equal(
    indexability(getDeliveryVertical("construction"), getDeliveryArea("hamilton")).index,
    true
  );
});

test("area FSAs come from the GTA coverage list, are unique and well-formed", () => {
  const seen = new Set();
  for (const area of DELIVERY_AREAS) {
    for (const fsa of area.fsas) {
      assert.match(fsa, /^[A-Z]\d[A-Z]$/);
      assert.ok(GTA150_FSA_CODES.has(fsa), `${fsa} not in GTA150 coverage`);
      assert.ok(!seen.has(fsa), `${fsa} in two areas`);
      seen.add(fsa);
    }
  }
  const registry = JSON.parse(
    readFileSync(
      new URL("services/pricing-engine/porterchain_pricing/data/gta150_fsa_registry.json", repo)
    )
  );
  // 334 = registry FSAs within the 150 km service radius (329) + 5 downtown hub overrides.
  assert.equal(ENTITY_FACTS.coverageFsaCount, GTA150_FSA_CODES.size);
  assert.equal(COVERAGE_FSA_COUNT, GTA150_FSA_CODES.size);
  assert.equal(
    GTA150_FSA_CODES.size,
    registry.fsas.filter(
      (r) => r.active !== false && r.distance_km_from_hub <= registry.tile.radius_km
    ).length + 5
  );
  const reg = new Map(registry.fsas.map((r) => [r.code, r]));
  const dt = getDeliveryArea("downtown-toronto");
  const meanLat = dt.fsas.reduce((s, c) => s + reg.get(c).lat, 0) / dt.fsas.length;
  assert.ok(Math.abs(meanLat - dt.lat) < 0.001, "centroid matches registry");
});

test("every page has unique, specific content", () => {
  const titles = new Set();
  const answers = new Set();
  for (const p of listDeliveryPages()) {
    const v = getDeliveryVertical(p.vertical);
    const a = getDeliveryArea(p.area);
    const c = buildDeliveryPageContent(v, a);
    titles.add(c.metaTitle);
    answers.add(c.answer);
    assert.ok(c.metaDescription.length <= 200, `${p.path} description too long`);
    assert.ok(c.answer.includes(a.name) && c.answer.includes(a.fsas[0]));
    assert.ok(c.faqs.length >= 6);
    assert.ok(c.faqs.some((f) => f.answer.includes(a.fsas.join(", "))));
    assert.ok(c.nearby.length > 0 && !c.nearby.some((n) => n.slug === a.slug));
    for (const n of c.nearby) {
      assert.ok(
        listDeliveryPages().some((q) => q.vertical === v.slug && q.area === n.slug),
        "nearby link exists"
      );
    }
  }
  assert.equal(titles.size, 88);
  assert.equal(answers.size, 88);
});

test("JSON-LD for every page validates (Service + Offer, FAQPage, BreadcrumbList)", () => {
  let checked = 0;
  for (const p of listDeliveryPages()) {
    const v = getDeliveryVertical(p.vertical);
    const a = getDeliveryArea(p.area);
    const content = buildDeliveryPageContent(v, a);
    const docs = [
      buildDeliveryServiceJsonLd(v, a, { baseUrl: BASE, locale: "en" }),
      buildDeliveryFaqJsonLd(content.faqs),
      buildDeliveryBreadcrumbJsonLd(deliveryBreadcrumbs("en", v, a), BASE),
    ];
    for (const doc of docs) {
      assert.deepEqual(validateJsonLd(doc), [], `${p.path} ${doc["@type"]}`);
      checked += 1;
    }
    assert.equal(docs[0].url, `${BASE}/en/${p.path}`);
    assert.equal(docs[2].itemListElement.at(-1).item, `${BASE}/en/${p.path}`);
  }
  assert.equal(checked, 264);
});

test("validator catches dishonest or broken schema", () => {
  const v = getDeliveryVertical("pharmacy");
  const a = getDeliveryArea("north-york");
  const svc = buildDeliveryServiceJsonLd(v, a, { baseUrl: BASE, locale: "en" });
  const faked = { ...svc, offers: { ...svc.offers, price: "9.99" } };
  assert.ok(validateJsonLd(faked).some((e) => e.includes("price must not be invented")));
  assert.equal(buildDeliveryFaqJsonLd([{ question: " ", answer: "" }]), null);
});

test("nearby areas are sorted by distance", () => {
  const near = nearbyAreas(getDeliveryArea("mississauga"));
  const km = near.map((n) => n.kmApart);
  assert.deepEqual(
    km,
    [...km].sort((x, y) => x - y)
  );
  assert.ok(near.some((n) => n.slug === "etobicoke" || n.slug === "brampton"));
});

test("llms.txt lists the facts page, delivery hub and calculator", () => {
  const llms = readFileSync(new URL("website/public/llms.txt", repo), "utf8");
  for (const path of ["/en/facts", "/en/delivery", "/en/delivery-cost-calculator"]) {
    assert.ok(llms.includes(`https://porterchain.com${path}`), path);
  }
});

/** Every "<n> postal areas / FSAs" claim in public copy must equal the generated FSA list. */
test("coverage count is in sync across facts, llms.txt and site copy", () => {
  const web = new URL("website/", repo);
  const files = [];
  const walk = (dir) => {
    for (const name of readdirSync(dir)) {
      if (name === "generated" || name === "node_modules" || name.startsWith(".")) continue;
      const child = new URL(name, dir.href.endsWith("/") ? dir : `${dir.href}/`);
      if (statSync(child).isDirectory()) walk(new URL(`${child.href}/`));
      else if (/\.(tsx?|json|txt|md)$/.test(name) && !/\.test\./.test(name)) files.push(child);
    }
  };
  walk(new URL("src/", web));
  walk(new URL("messages/", web));
  files.push(new URL("public/llms.txt", web));
  const claim =
    /\b(\d{3})\s*(?:GTA\s+)?(?:postal areas|postal codes|FSAs|forward sortation areas|zones postales|régions de tri)/gi;
  const found = [];
  for (const file of files) {
    const text = readFileSync(file, "utf8");
    for (const m of text.matchAll(claim))
      found.push({ file: file.pathname.split("/website/")[1], n: Number(m[1]) });
  }
  const wrong = found.filter((f) => f.n !== GTA150_FSA_CODES.size);
  assert.deepEqual(wrong, [], `coverage must say ${GTA150_FSA_CODES.size}`);
  assert.ok(
    found.some((f) => f.file === "public/llms.txt"),
    "llms.txt states the coverage count"
  );
});

test("llms.txt lists every industry hub and the industry count", () => {
  const llms = readFileSync(new URL("website/public/llms.txt", repo), "utf8");
  for (const v of DELIVERY_VERTICALS) {
    assert.ok(llms.includes(`https://porterchain.com/en/delivery/${v.slug} `), v.slug);
  }
  assert.ok(
    llms.includes(`${DELIVERY_VERTICALS.length} industries x ${DELIVERY_AREAS.length} GTA areas`),
    "hub line counts"
  );
});

test("furniture hub states the service limits from the commercial terms", () => {
  const v = getDeliveryVertical("furniture");
  assert.ok(v?.hub, "furniture hub content");
  const text = JSON.stringify(v.hub);
  for (const needle of ["Threshold", "50 lb", "liftgate", "assembl", "carton"]) {
    assert.ok(text.toLowerCase().includes(needle.toLowerCase()), needle);
  }
  assert.ok(v.hub.faqs.length >= 6);
  assert.deepEqual(validateJsonLd(buildDeliveryFaqJsonLd(v.hub.faqs)), []);
  assert.deepEqual(v.vehicles, ["cargo_van", "box_16"]);
});
