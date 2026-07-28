/**
 * Golden-set retrieval eval for Capacity Guide knowledge (L3).
 * Run: pnpm --filter @porterchain/website exec tsx src/lib/home/guide-knowledge.eval.ts
 * Or: npx tsx website/src/lib/home/guide-knowledge.eval.ts
 */

import { retrieveGuideKnowledge } from "./guide-knowledge";

type Case = {
  query: string;
  expectIdIncludes: string[];
};

const CASES: Case[] = [
  {
    query: "How does pricing work?",
    expectIdIncludes: ["pricing", "charter-pricing", "business-faq-pricing"],
  },
  {
    query: "What vehicles are available?",
    expectIdIncludes: ["vehicle", "charter-vehicles", "business-faq-vehicles"],
  },
  {
    query: "Do you cover Mississauga and the GTA?",
    expectIdIncludes: ["coverage", "charter-coverage", "gta", "areas"],
  },
  {
    query: "How do I track my shipment?",
    expectIdIncludes: ["track", "charter-tracking"],
  },
  {
    query: "construction jobsite delivery materials",
    expectIdIncludes: ["construction", "cluster-construction"],
  },
  {
    query: "What is Porterchain?",
    expectIdIncludes: ["charter-identity", "identity"],
  },
];

function passCase(c: Case): boolean {
  const hits = retrieveGuideKnowledge(c.query, { limit: 5 });
  const blob = hits.map((h) => h.id).join(" ");
  return c.expectIdIncludes.some((needle) => blob.includes(needle));
}

function main() {
  let passed = 0;
  for (const c of CASES) {
    const ok = passCase(c);
    if (ok) passed += 1;
    const hits = retrieveGuideKnowledge(c.query, { limit: 3 }).map((h) => h.id);
    console.log(`${ok ? "PASS" : "FAIL"} | ${c.query}`);
    console.log(`       hits: ${hits.join(", ") || "(none)"}`);
  }
  const total = CASES.length;
  console.log(`\n${passed}/${total} passed`);
  if (passed < total) process.exitCode = 1;
}

main();
