/**
 * Messages shipped to the browser (NextIntlClientProvider).
 *
 * Server components read the full catalogue from `getRequestConfig`; only namespaces used by
 * client components ("use client" files and everything they import) need to be serialised into
 * every HTML response. Shipping all ~450 KB of JSON on every page was the single biggest payload
 * on the marketing site (website Phase 1, Oct 2026).
 *
 * Guarded by `client-messages.test.mts` (pnpm test:seo): it walks the client import graph and
 * fails if a `useTranslations("…")` namespace is not covered here. Add the namespace (or a parent)
 * when you add a client component that translates.
 */
export const CLIENT_MESSAGE_NAMESPACES = [
  "blog",
  "booking.track",
  "businessPage",
  "capacityOps",
  "common.brand",
  "common.cta",
  "corporate.contact.form",
  "corporate.contact.info.whatsappChat",
  "corporate.nav",
  "corporate.platformBridge",
  "footer",
  "homeChooser",
  "homePage.calculator",
  "legal",
  "login",
  "marketing.consent",
  "marketing.priceBar",
  "portal.customer",
  "productTrust",
  "vehiclePartner",
] as const;

type Messages = Record<string, unknown>;

function isRecord(value: unknown): value is Messages {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Copy only `namespaces` (dot paths) out of `messages`, preserving nesting. */
export function pickMessages(
  messages: Messages,
  namespaces: readonly string[] = CLIENT_MESSAGE_NAMESPACES
): Messages {
  const out: Messages = {};
  for (const namespace of namespaces) {
    const keys = namespace.split(".");
    let source: unknown = messages;
    for (const key of keys) {
      source = isRecord(source) ? source[key] : undefined;
    }
    if (source === undefined) continue;
    let target = out;
    keys.forEach((key, index) => {
      if (index === keys.length - 1) {
        target[key] = source;
        return;
      }
      if (!isRecord(target[key])) target[key] = {};
      target = target[key] as Messages;
    });
  }
  return out;
}
