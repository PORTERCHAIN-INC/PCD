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
export function buildChatWhatsAppMessage(
  localeOrOpts?:
    | string
    | {
        locale?: string;
        visitorId?: string;
        utmSource?: string;
        utmMedium?: string;
        utmCampaign?: string;
        path?: string;
      }
): string {
  const opts =
    typeof localeOrOpts === "string" || localeOrOpts == null
      ? { locale: localeOrOpts }
      : localeOrOpts;
  const locale = opts.locale;
  const base =
    locale === "fr"
      ? "Bonjour Porterchain — j'aimerais discuter de la capacité véhicule et chauffeur pour mon entreprise."
      : "Hi Porterchain — I'd like to chat about vehicle-and-driver capacity for my business.";
  const lines = [base];
  const utmSource = opts.utmSource || "whatsapp";
  const utmMedium = opts.utmMedium || "fab";
  const utmCampaign = opts.utmCampaign || "capacity_chat";
  lines.push(`utm_source=${utmSource}&utm_medium=${utmMedium}&utm_campaign=${utmCampaign}`);
  if (opts.path) {
    lines.push(`page=${opts.path}`);
  }
  if (opts.visitorId) {
    // Staff can claim this visitor session on the lead workbench.
    lines.push(`claim=${opts.visitorId.slice(0, 12)}`);
  }
  return lines.join("\n");
}
