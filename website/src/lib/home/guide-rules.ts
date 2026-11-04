/**
 * Capacity Guide — rule-based engine (doc 60 R2: no external AI vendors).
 * Pure functions: classify the visitor's message, extract contact details,
 * and pick the next reply. The route runs the side effects (CRM, slots).
 */
import type { GuideSessionState } from "./guide-session";

export type GuideIntent = "track" | "book" | "quote" | "contact" | "question";

const EMAIL_RE = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i;
const PHONE_RE = /(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}/;
const TRACK_RE = /\b(PC[A-Z0-9-]{4,}|[A-Z]{2,4}-?\d{5,})\b/i;

export function extractEmail(text: string): string | undefined {
  return text.match(EMAIL_RE)?.[0].toLowerCase();
}

export function extractPhone(text: string): string | undefined {
  const stripped = text.replace(EMAIL_RE, " ");
  const m = stripped.match(PHONE_RE)?.[0];
  if (!m) return undefined;
  const digits = m.replace(/\D/g, "");
  return digits.length === 10 ? `+1${digits}` : `+${digits}`;
}

export function extractTrackingNumber(text: string): string | undefined {
  return text.match(TRACK_RE)?.[1]?.toUpperCase();
}

export function classifyIntent(text: string): GuideIntent {
  const t = text.toLowerCase();
  if (/\b(track|tracking|where is|status of|my (order|parcel|package|delivery))\b/.test(t))
    return "track";
  if (/\b(book|schedule|call me|meeting|meet|appointment|talk to|speak)\b/.test(t)) return "book";
  if (/\b(price|pricing|cost|quote|rate|how much|estimate)\b/.test(t)) return "quote";
  if (EMAIL_RE.test(text) || PHONE_RE.test(text)) return "contact";
  return "question";
}

/** Slot choice like "1", "#2", "option 3" (1-based). */
export function parseSlotChoice(text: string): number | undefined {
  const m = text.trim().match(/^(?:#|option\s*|slot\s*)?([1-4])\.?$/i);
  return m ? Number(m[1]) - 1 : undefined;
}

export function meetingTypeFrom(text: string): "call" | "meeting" {
  return /\b(in[- ]person|meet(ing)? (in|at)|visit|office)\b/i.test(text) ? "meeting" : "call";
}

export function contactPrompt(state: GuideSessionState): string | null {
  if (state.email && state.phone) return null;
  if (state.email) return "What's the best mobile number to reach you?";
  if (state.phone) return "What's your work email so the team can send details?";
  return "Share your work email and mobile number and our team will follow up with a tailored quote.";
}

export const QUOTE_REPLY =
  "Prices depend on distance, vehicle size and timing. Get an instant price at /delivery-cost-calculator — business volume pricing is set up after a short call.";
export const FALLBACK_REPLY =
  "I can help with pricing, coverage, vehicles, proof of delivery, APIs and business accounts. You can also get an instant price at /delivery-cost-calculator.";
