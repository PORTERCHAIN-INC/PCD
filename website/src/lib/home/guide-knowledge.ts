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
    title: "What PorterChain is",
    body: "PorterChain is the operating platform that helps businesses simplify, automate, and manage local logistics in the Greater Toronto Area. Evidence behind that promise: professional drivers and vehicles, business portal (quotes, booking, tracking, proof, reports), AI assistance, APIs, and dedicated logistics support. Not a consumer courier marketplace.",
    tags: ["identity", "platform", "logistics", "charter", "gta", "business account", "what"],
    source: "charter",
  },
  {
    id: "charter-pricing",
    title: "How pricing works",
    body: "Pricing is quote-based on vehicle class, distance, stops, urgency (same-day vs scheduled), and handling. Never invent dollar amounts. Business accounts bring quotes, booking, and tracking together; transportation capacity and price are confirmed in writing before dispatch. Request via /contact?intent=quote or /business.",
    tags: ["pricing", "quote", "billing", "cost", "rate", "business account"],
    source: "charter",
  },
  {
    id: "charter-coverage",
    title: "Coverage",
    body: "Service focuses on the Greater Toronto Area — Toronto, Peel (Mississauga, Brampton), York (Vaughan, Markham), and Durham. Lanes are quote-based for pickup and delivery within the GTA.",
    tags: [
      "coverage",
      "gta",
      "areas",
      "mississauga",
      "toronto",
      "peel",
      "york",
      "durham",
      "brampton",
      "vaughan",
    ],
    source: "charter",
  },
  {
    id: "charter-vehicles",
    title: "Vehicles",
    body: "Transportation layer: sedan, SUV, pickup, cargo van, sprinter van, 16 ft box truck, and 20 ft box truck — each with a professional driver. Match vehicle to weight, dimensions, and site access across GTA lanes.",
    tags: [
      "vehicles",
      "fleet",
      "box truck",
      "van",
      "driver",
      "transportation",
      "sedan",
      "suv",
      "pickup",
    ],
    source: "charter",
  },
  {
    id: "charter-tracking",
    title: "Tracking and proof of delivery",
    body: "Business platform includes live tracking and proof of delivery (photo, signature where agreed). Guests look up status at /track. If a tracking number is known, open /track/{number}. Never invent live status — only point to the tracking page or ask for the number.",
    tags: ["tracking", "pod", "proof", "status", "signature", "photo"],
    source: "charter",
  },
  {
    id: "charter-paths",
    title: "Next steps and paths",
    body: "Get a Business Account at /business. Talk to a Logistics Specialist or request a quote at /contact?intent=quote. Drivers join as vehicle partners at /vehicle-partner. Track a shipment at /track. Always collect work email and mobile so the team can follow up.",
    tags: ["cta", "merchants", "drivers", "quote", "business account", "contact", "email", "phone"],
    source: "charter",
  },
  {
    id: "charter-same-day",
    title: "Same-day and overflow capacity",
    body: "Same-day and urgent overflow are core use cases when a driver is out, a truck is down, or demand spikes. Share pickup, drop, vehicle class, and time window. Availability depends on cut-off, zone, and vehicle class — confirmed when quoting. Recurring routes and dedicated programs are also available for predictable volume.",
    tags: ["same-day", "overflow", "urgent", "emergency", "backup", "recurring"],
    source: "charter",
  },
  {
    id: "charter-business-account",
    title: "Business account capabilities",
    body: "A PorterChain Business Account lets ops generate instant quotes, book deliveries, track shipments live, download proof of delivery, view invoices and reports, connect via APIs, use AI assistance, and work with dedicated logistics support — all from one platform for local GTA logistics.",
    tags: ["business account", "dashboard", "booking", "quotes", "api", "reports", "portal"],
    source: "charter",
  },
  {
    id: "charter-industries",
    title: "Industries served",
    body: "PorterChain serves GTA B2B operations across manufacturing, construction, industrial supply, electrical distribution, HVAC, plumbing, medical and pharmacy, retail, and wholesale. Capacity adapts to jobsite windows, counter-to-jobsite runs, warehouse distribution, and peak overflow.",
    tags: [
      "industries",
      "manufacturing",
      "construction",
      "wholesale",
      "medical",
      "retail",
      "hvac",
      "plumbing",
      "electrical",
      "industrial",
    ],
    source: "charter",
  },
  {
    id: "charter-api",
    title: "APIs and integrations",
    body: "Business accounts can connect order creation, tracking, and reporting through APIs. Documentation is provided during onboarding. Custom integrations are scoped with the logistics and technology team after account setup.",
    tags: ["api", "integrations", "webhook", "csv", "onboarding", "technology"],
    source: "charter",
  },
  {
    id: "charter-drivers",
    title: "Driver and vehicle partners",
    body: "Eligible vehicle partners join the GTA network for structured routes, clear instructions, and a dedicated driver portal. Apply at /vehicle-partner. Vehicle fit and onboarding are reviewed by the team.",
    tags: ["drivers", "vehicle partner", "partner", "join", "drive"],
    source: "charter",
  },
  {
    id: "charter-contact-followup",
    title: "How follow-up works",
    body: "Sharing a work email and mobile phone lets PorterChain save the conversation and have a logistics specialist follow up with written capacity options. Contact capture is required before booking a call. Visitors can also open /business or /contact?intent=quote.",
    tags: ["contact", "email", "phone", "follow-up", "specialist", "lead"],
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
  for (const cluster of FAQ_CLUSTERS.slice(0, 24)) {
    out.push({
      id: `cluster-${cluster.slug}-intro`,
      title: cluster.title,
      body: `${cluster.title}. ${cluster.intro}`,
      tags: ["industry", cluster.slug, ...cluster.industrySlugs.slice(0, 3)],
      source: "faq-cluster",
    });
    for (const [i, item] of cluster.items.slice(0, 10).entries()) {
      out.push({
        id: `cluster-${cluster.slug}-${i}`,
        title: item.question,
        body: `${item.question} ${item.answer}`,
        tags: ["industry", cluster.slug, "faq"],
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
    if (/\b(vehicle|truck|van|fleet|sedan|suv|pickup)\b/.test(q) && chunk.id.includes("vehicle")) {
      score += 4;
    }
    if (
      /\b(same.?day|overflow|urgent|emergency|backup)\b/.test(q) &&
      chunk.id.includes("same-day")
    ) {
      score += 5;
    }
    if (
      /\b(account|dashboard|portal|booking|api|integrat)\b/.test(q) &&
      (chunk.id.includes("business-account") || chunk.id.includes("api"))
    ) {
      score += 4;
    }
    if (
      /\b(industr|manufactur|construct|wholesale|medical|retail|hvac|plumb|electric)\b/.test(q) &&
      chunk.id.includes("industries")
    ) {
      score += 4;
    }
    if (/\b(driver|partner|join|drive)\b/.test(q) && chunk.id.includes("drivers")) {
      score += 4;
    }

    return { ...chunk, score };
  });

  return scored
    .filter((c) => c.score > 1.0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}
