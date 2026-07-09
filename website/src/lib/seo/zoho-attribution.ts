import type { Attribution } from "./attribution";

declare global {
  interface Window {
    $zoho?: {
      salesiq?: {
        ready?: () => void;
        floatwindow?: { on?: (event: string, cb: () => void) => void };
        visitor?: {
          info?: (fields: Record<string, string>) => void;
        };
      };
    };
  }
}

export {};

/** Push session attribution into Zoho SalesIQ visitor fields (CRM lead source tagging). */
export function pushAttributionToZoho(att: Attribution): void {
  if (typeof window === "undefined") return;
  try {
    const visitor = window.$zoho?.salesiq?.visitor;
    if (!visitor?.info) return;

    const fields: Record<string, string> = {};
    if (att.from) fields["PCD From"] = att.from;
    if (att.sourcePage) fields["PCD Source Page"] = att.sourcePage;
    if (att.locale) fields["PCD Locale"] = att.locale;
    if (att.utm_source) fields["UTM Source"] = att.utm_source;
    if (att.utm_medium) fields["UTM Medium"] = att.utm_medium;
    if (att.utm_campaign) fields["UTM Campaign"] = att.utm_campaign;
    if (att.landingPageUrl) fields["PCD Landing URL"] = att.landingPageUrl;

    if (Object.keys(fields).length > 0) {
      visitor.info(fields);
    }
  } catch {
    /* SalesIQ API varies by plan */
  }
}
