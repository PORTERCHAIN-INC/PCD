/**
 * CASL express-consent wording. Must match the API's CASL_FORM_TEXT
 * (apps/api/.../lead_consent.py) — the server records its own copy + version.
 */
export const CASL_FORM_TEXT_VERSION = "casl_v2_form_marketing";

export const CASL_FORM_TEXT = {
  en:
    "Yes, send me PorterChain delivery news, offers and tips by email. " +
    "I can unsubscribe at any time. PorterChain Logistics Inc., Toronto ON, sales@porterchain.com",
  fr:
    "Oui, envoyez-moi par courriel les nouvelles, offres et conseils de livraison de PorterChain. " +
    "Je peux me désabonner en tout temps. PorterChain Logistics Inc., Toronto ON, sales@porterchain.com",
} as const;

export function caslText(locale: string | undefined): string {
  return (locale ?? "").toLowerCase().startsWith("fr") ? CASL_FORM_TEXT.fr : CASL_FORM_TEXT.en;
}
