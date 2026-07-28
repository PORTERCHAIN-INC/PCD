/**
 * Welcome-page capacity guide — curated Q&A (no LLM).
 * Keyword match returns grounded answers + next-step CTAs.
 */

export type GuideAction = {
  labelKey: string;
  href: string;
};

export type GuideTopic = {
  id: string;
  /** Lowercased keywords / phrases that activate this topic */
  keywords: string[];
  /** i18n keys under homeChooser.guide.topics.{id}.* */
  promptKeys: string[];
};

export const GUIDE_TOPICS: readonly GuideTopic[] = [
  {
    id: "what",
    keywords: [
      "what is",
      "porterchain",
      "who are",
      "about",
      "network",
      "capacity network",
      "what do you",
      "qu est",
      "quest-ce",
      "c est quoi",
      "a propos",
      "reseau",
    ],
    promptKeys: ["what"],
  },
  {
    id: "pricing",
    keywords: [
      "price",
      "pricing",
      "cost",
      "quote",
      "how much",
      "rate",
      "billing",
      "tariff",
      "fee",
      "prix",
      "tarif",
      "tarification",
      "devis",
      "cout",
      "facturation",
    ],
    promptKeys: ["pricing"],
  },
  {
    id: "industries",
    keywords: [
      "industry",
      "industries",
      "construction",
      "medical",
      "pharmacy",
      "wholesale",
      "manufacturing",
      "retail",
      "who do you serve",
      "sectors",
      "secteur",
      "medical",
      "pharmacie",
      "gros",
      "fabrication",
      "detail",
    ],
    promptKeys: ["industries"],
  },
  {
    id: "sameday",
    keywords: [
      "same day",
      "same-day",
      "urgent",
      "emergency",
      "asap",
      "today",
      "overflow",
      "backup",
      "jour meme",
      "urgence",
      "debordement",
      "aujourd",
    ],
    promptKeys: ["sameday"],
  },
  {
    id: "vehicles",
    keywords: [
      "vehicle",
      "van",
      "truck",
      "box truck",
      "sprinter",
      "sedan",
      "suv",
      "pickup",
      "fleet",
      "what vehicles",
      "vehicule",
      "camion",
      "fourgon",
      "flotte",
    ],
    promptKeys: ["vehicles"],
  },
  {
    id: "merchants",
    keywords: [
      "merchant",
      "business",
      "shipper",
      "company",
      "b2b",
      "for my business",
      "account",
      "marchand",
      "entreprise",
      "expediteur",
      "compte",
    ],
    promptKeys: ["merchants"],
  },
  {
    id: "drivers",
    keywords: [
      "driver",
      "partner",
      "join",
      "drive with",
      "vehicle partner",
      "become a driver",
      "owner operator",
      "chauffeur",
      "partenaire",
      "devenir",
    ],
    promptKeys: ["drivers"],
  },
  {
    id: "areas",
    keywords: [
      "area",
      "gta",
      "toronto",
      "ontario",
      "mississauga",
      "brampton",
      "where",
      "coverage",
      "service area",
      "rgt",
      "ou opere",
      "couverture",
      "zone",
    ],
    promptKeys: ["areas"],
  },
  {
    id: "tracking",
    keywords: [
      "track",
      "tracking",
      "pod",
      "proof",
      "signature",
      "gps",
      "status",
      "visibility",
      "suivi",
      "preuve",
      "signature",
    ],
    promptKeys: ["tracking"],
  },
  {
    id: "start",
    keywords: [
      "start",
      "get started",
      "how do i",
      "next step",
      "book",
      "request",
      "contact",
      "commencer",
      "demarrer",
      "prochaine",
      "contacter",
    ],
    promptKeys: ["start"],
  },
] as const;

export type GuideTopicId = (typeof GUIDE_TOPICS)[number]["id"];

/** Suggested chip order on the welcome console */
export const GUIDE_SUGGESTION_IDS: readonly GuideTopicId[] = [
  "pricing",
  "sameday",
  "industries",
  "vehicles",
  "drivers",
] as const;

export function normalizeGuideQuery(raw: string): string {
  return raw
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9\s-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function matchGuideTopic(query: string): GuideTopicId | "fallback" {
  const q = normalizeGuideQuery(query);
  if (!q) return "fallback";

  let best: { id: GuideTopicId; score: number } | null = null;
  for (const topic of GUIDE_TOPICS) {
    let score = 0;
    for (const kw of topic.keywords) {
      if (q.includes(kw)) {
        score += kw.includes(" ") ? 3 : 2;
      }
    }
    if (score > 0 && (!best || score > best.score)) {
      best = { id: topic.id, score };
    }
  }
  return best?.id ?? "fallback";
}

export function guideActionsForTopic(
  topicId: GuideTopicId | "fallback",
  from: string
): GuideAction[] {
  const q = `from=${from}`;
  switch (topicId) {
    case "drivers":
      return [
        { labelKey: "actions.drivers", href: `/vehicle-partner?${q}` },
        { labelKey: "actions.quote", href: `/contact?intent=quote&${q}` },
      ];
    case "pricing":
      return [
        { labelKey: "actions.pricing", href: `/business?${q}#pricing` },
        { labelKey: "actions.quote", href: `/contact?intent=quote&${q}` },
      ];
    case "industries":
      return [
        { labelKey: "actions.industries", href: `/business?${q}#industries` },
        { labelKey: "actions.quote", href: `/contact?intent=quote&${q}` },
      ];
    case "vehicles":
      return [
        { labelKey: "actions.fleet", href: `/business?${q}#fleet` },
        { labelKey: "actions.quote", href: `/contact?intent=quote&${q}` },
      ];
    case "merchants":
    case "sameday":
    case "areas":
    case "tracking":
    case "start":
    case "what":
    case "fallback":
    default:
      return [
        { labelKey: "actions.merchants", href: `/business?${q}` },
        { labelKey: "actions.quote", href: `/contact?intent=quote&${q}` },
      ];
  }
}
