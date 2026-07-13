import { publicEnv } from "@/lib/env";

/** wa.me deep link with pre-filled message (WhatsApp Business Phase 1). */
export function buildWhatsAppDeepLink(message: string): string {
  const base = publicEnv.socialWhatsApp.replace(/\?.*$/, "");
  return `${base}?text=${encodeURIComponent(message)}`;
}

export function buildQuoteWhatsAppMessage(params: {
  name?: string;
  businessName?: string;
  urgency?: string;
  vehicle?: string;
  lanes?: string;
  source?: string;
}): string {
  const who = params.businessName?.trim() || params.name?.trim() || "my business";
  return [
    `Hi Porterchain — I just submitted a quote request for ${who}.`,
    params.urgency ? `Urgency: ${params.urgency}` : null,
    params.vehicle ? `Vehicle: ${params.vehicle}` : null,
    params.lanes ? `Lanes: ${params.lanes}` : null,
    params.source ? `Submitted from: ${params.source}` : null,
  ]
    .filter(Boolean)
    .join("\n");
}

/** Prefill for the mobile live-chat FAB (replaces Zoho on phone browsers). */
export function buildChatWhatsAppMessage(locale?: string): string {
  if (locale === "fr") {
    return "Bonjour Porterchain — j'aimerais discuter de la capacité véhicule et chauffeur pour mon entreprise.";
  }
  return "Hi Porterchain — I'd like to chat about vehicle-and-driver capacity for my business.";
}
