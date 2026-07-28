/**
 * Curated Capacity Guide knowledge corpus + lexical retrieval (L2).
 * Hybrid dense/pgvector deferred until Postgres image supports the extension.
 */

import businessEn from "../../../messages/business-en.json";
import { FAQ_CLUSTERS } from "@/lib/seo/content/faq-clusters";

export type KnowledgeChunk = {
  id: string;
  title: string;
  body: string;
  tags: string[];
  source: string;
};

const CHARTER_CHUNKS: KnowledgeChunk[] = [
  {
    id: "charter-identity",
    title: "What Porterchain is",
    body: "Porterchain is a Transportation Capacity Network. Customers buy vehicle-and-driver capacity for same-day overflow, urgent runs, recurring distribution, construction/jobsite, medical/pharmacy, wholesale, manufacturing, and retail. Porterchain is not a courier brand, trucking company identity, dispatch SaaS, fleet-management software SKU, or delivery marketplace.",
    tags: ["identity", "capacity", "network", "charter"],
    source: "charter",
  },
  {
    id: "charter-pricing",
    title: "How pricing works",
    body: "Pricing is quote-based on vehicle class, distance, stops, urgency (same-day vs scheduled), and handling. Never invent dollar amounts. Merchants pay for capacity executed — not software seats. Confirm capacity and price in writing before dispatch. Request a quote via /contact?intent=quote or /business.",
    tags: ["pricing", "quote", "billing"],
    source: "charter",
  },
  {
    id: "charter-coverage",
    title: "Coverage",
    body: "Primary coverage is the Greater Toronto Area and Ontario metros — Toronto, Mississauga, Brampton, Vaughan, Markham, Oakville, Hamilton, Kitchener-Waterloo, London, Niagara, and surrounding regions. Lanes are quote-based for pickup and delivery geographies.",
    tags: ["coverage", "gta", "ontario", "areas", "mississauga", "toronto"],
    source: "charter",
  },
  {
    id: "charter-vehicles",
    title: "Vehicles",
    body: "Vehicle classes include sedan, SUV, pickup, cargo van, sprinter van, 16 ft box truck, and 20 ft box truck. Ontario G licence classes apply for drivers today. Match vehicle to weight, dimensions, and site access.",
    tags: ["vehicles", "fleet", "box truck", "van"],
    source: "charter",
  },
  {
    id: "charter-tracking",
    title: "Tracking and proof of delivery",
    body: "Shipments can include tracking links and proof of delivery (photo, signature where agreed). Guests look up status at /track. If a tracking number is known, open /track/{number}. Never invent live status — only point to the tracking page or ask for the number.",
    tags: ["tracking", "pod", "proof", "status"],
    source: "charter",
  },
  {
    id: "charter-paths",
    title: "Next steps and paths",
    body: "Merchants explore capacity at /business. Drivers join as vehicle partners at /vehicle-partner. Request capacity or a written quote at /contact?intent=quote. Track a shipment at /track.",
    tags: ["cta", "merchants", "drivers", "quote"],
    source: "charter",
  },
];

function businessFaqChunks(): KnowledgeChunk[] {
  const items = businessEn.faq?.items ?? {};
  return Object.entries(items).map(([key, item]) => ({
    id: `business-faq-${key}`,
    title: item.question,
    body: `${item.question} ${item.answer}`,
    tags: ["faq", "business", key],
    source: "business-faq",
  }));
}

function answerChunks(): KnowledgeChunk[] {
  const answers = businessEn.answers ?? {};
  const out: KnowledgeChunk[] = [];
  for (const [key, value] of Object.entries(answers)) {
    if (
      value &&
      typeof value === "object" &&
      "question" in value &&
      "answer" in value &&
      typeof value.question === "string" &&
      typeof value.answer === "string"
    ) {
      out.push({
        id: `business-answers-${key}`,
        title: value.question,
        body: `${value.question} ${value.answer}`,
        tags: ["faq", "answers", key],
        source: "business-answers",
      });
    }
  }
  return out;
}

function faqClusterChunks(): KnowledgeChunk[] {
  const out: KnowledgeChunk[] = [];
  for (const cluster of FAQ_CLUSTERS.slice(0, 12)) {
    out.push({
      id: `cluster-${cluster.slug}-intro`,
      title: cluster.title,
      body: `${cluster.title}. ${cluster.intro}`,
      tags: ["industry", cluster.slug, ...cluster.industrySlugs.slice(0, 3)],
      source: "faq-cluster",
    });
    for (const [i, item] of cluster.items.slice(0, 6).entries()) {
      out.push({
        id: `cluster-${cluster.slug}-${i}`,
        title: item.question,
        body: `${item.question} ${item.answer}`,
        tags: ["industry", cluster.slug],
        source: "faq-cluster",
      });
    }
  }
  return out;
}

let _corpus: KnowledgeChunk[] | null = null;

export function getGuideKnowledgeCorpus(): KnowledgeChunk[] {
  if (!_corpus) {
    _corpus = [...CHARTER_CHUNKS, ...businessFaqChunks(), ...answerChunks(), ...faqClusterChunks()];
  }
  return _corpus;
}

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9àâäéèêëïîôùûüç\s-]/gi, " ")
    .split(/\s+/)
    .filter((t) => t.length > 1);
}

/** Lexical retrieval with light tag boost (BM25-ish TF scoring). */
export function retrieveGuideKnowledge(
  query: string,
  opts: { limit?: number } = {}
): Array<KnowledgeChunk & { score: number }> {
  const limit = opts.limit ?? 5;
  const qTokens = tokenize(query);
  if (qTokens.length === 0) return [];

  const scored = getGuideKnowledgeCorpus().map((chunk) => {
    const hay = tokenize(`${chunk.title} ${chunk.body} ${chunk.tags.join(" ")}`);
    const tf = new Map<string, number>();
    for (const t of hay) tf.set(t, (tf.get(t) ?? 0) + 1);

    let score = 0;
    for (const qt of qTokens) {
      const c = tf.get(qt) ?? 0;
      if (c > 0) score += 1.4 + Math.log(1 + c);
    }
    // Soft substring only for tokens length >= 4 to reduce noise
    for (const qt of qTokens) {
      if (qt.length < 4) continue;
      for (const [tok, n] of tf) {
        if (tok === qt) continue;
        if (tok.includes(qt) || qt.includes(tok)) score += 0.08 * Math.min(n, 3);
      }
    }
    for (const tag of chunk.tags) {
      if (qTokens.some((qt) => tag === qt || (qt.length >= 4 && tag.includes(qt)))) {
        score += 1.2;
      }
    }
    if (chunk.source === "charter") score += 0.5;

    const q = query.toLowerCase();
    if (/\b(track|tracking|shipment|pod)\b/.test(q) && chunk.id.includes("tracking")) {
      score += 6;
    }
    if (
      /\b(cover|coverage|gta|mississauga|toronto|ontario|areas?)\b/.test(q) &&
      (chunk.id.includes("coverage") || chunk.id.includes("gta") || chunk.id.includes("areas"))
    ) {
      score += 5;
    }
    if (/\b(price|pricing|cost|quote|rate)\b/.test(q) && chunk.id.includes("pricing")) {
      score += 4;
    }
    if (/\b(vehicle|truck|van|fleet)\b/.test(q) && chunk.id.includes("vehicle")) {
      score += 4;
    }

    return { ...chunk, score };
  });

  return scored
    .filter((c) => c.score > 1.2)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}
