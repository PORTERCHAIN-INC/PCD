/**
 * Customer case studies for the homepage. A study renders ONLY when `published` is true, which
 * must mean the customer has given written permission to be named. Never invent quotes, numbers
 * or logos — fill `quote` / `facts` from the customer's approved text.
 */
export type CaseStudy = {
  id: string;
  customer: string;
  published: boolean;
  headline: string;
  quote?: { text: string; author: string; role: string };
  facts: Array<{ label: string; value: string }>;
  href?: string;
};

export const CASE_STUDIES: CaseStudy[] = [
  {
    // Slot reserved for Kaylulu (Shopify merchant on the contract schedule). Hidden until
    // Kaylulu approves the wording and the use of its name.
    id: "kaylulu",
    customer: "Kaylulu",
    published: false,
    headline: "",
    facts: [],
  },
];

export const PUBLISHED_CASE_STUDIES = CASE_STUDIES.filter(
  (s) => s.published && s.headline.trim().length > 0
);
