import type { NicheLandingContent } from "@/components/seo/IndustryLandingView";

const FAQ_KEYS = ["q1", "q2", "q3", "q4", "q5", "q6", "q7"] as const;
const ANSWER_KEYS = ["a1", "a2", "a3", "a4", "a5", "a6", "a7"] as const;

export function collectNicheFaqItems(
  faq: NicheLandingContent["faq"]
): { question: string; answer: string }[] {
  if (!faq) return [];

  const items: { question: string; answer: string }[] = [];
  for (let i = 0; i < FAQ_KEYS.length; i++) {
    const q = faq[FAQ_KEYS[i] as keyof typeof faq];
    const a = faq[ANSWER_KEYS[i] as keyof typeof faq];
    if (typeof q === "string" && typeof a === "string" && q.length > 0) {
      items.push({ question: q, answer: a });
    }
  }
  return items;
}

export function buildPersonaItems(
  personas: NicheLandingContent["personas"],
  trustHref?: string,
  trustLabel?: string
) {
  if (!personas?.items) return null;

  const order = [
    "vendor",
    "contractor",
    "projectManager",
    "operations",
    "tradePartner",
    "architect",
    "legalProcurement",
  ] as const;

  const items = order
    .map((key) => {
      const item = personas.items?.[key];
      if (!item?.title || !item?.description) return null;
      return {
        title: item.title,
        description: item.description,
        trustHref: key === "legalProcurement" ? trustHref : undefined,
        trustLabel: key === "legalProcurement" ? trustLabel : undefined,
      };
    })
    .filter((item): item is NonNullable<typeof item> => item !== null);

  if (items.length === 0) return null;

  return {
    label: personas.label,
    title: personas.title,
    subtitle: personas.subtitle,
    items,
  };
}
