/**
 * Customer testimonials for the website ReviewsProof section.
 *
 * RULES (readiness audit #13 — no fake reviews):
 * - Only add quotes a real customer wrote or approved in writing; keep the approval on file.
 * - `verified: true` only after the person/company agreed to be named publicly.
 * - Unverified or placeholder entries are filtered out and never rendered.
 * - Do NOT add AggregateRating/Review JSON-LD for our own business — Google treats
 *   self-serving reviews as ineligible for rich results.
 */
export type CustomerReview = {
  quote: string;
  author: string;
  role?: string;
  company?: string;
  /** 1–5, only if the customer gave a star rating (e.g. copied from Google). */
  rating?: number;
  source?: "google" | "direct" | "case-study";
  /** ISO date the review was given. */
  date?: string;
  verified: boolean;
  locale?: "en" | "fr";
};

export const CUSTOMER_REVIEWS: CustomerReview[] = [
  // Example shape (keep commented until a real, approved quote exists):
  // {
  //   quote: "…",
  //   author: "Jane D.",
  //   role: "Operations Manager",
  //   company: "Example Supply Co.",
  //   rating: 5,
  //   source: "google",
  //   date: "2026-10-01",
  //   verified: true,
  // },
];

export function publishableReviews(locale: string, max = 3): CustomerReview[] {
  return CUSTOMER_REVIEWS.filter(
    (r) =>
      r.verified &&
      r.quote.trim().length > 0 &&
      r.author.trim().length > 0 &&
      (!r.locale || r.locale === locale)
  ).slice(0, max);
}
