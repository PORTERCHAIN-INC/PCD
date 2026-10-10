/**
 * One booking module for web (website /book, customer portal Send) and mobile (BookScreen).
 * Pure TypeScript: no React, no fetch. Rules here are the single source of truth for the
 * customer booking flow: vehicles, ≤5 drops, validation, quote payload, price text, copy.
 */

export type BookingLocale = "en" | "fr";
export type VehicleId = "sedan_suv" | "cargo_van" | "box_16";

export const MAX_DROPS = 5;
export const MIN_FILL_MS = 2500;

export const BOOKING_VEHICLES: ReadonlyArray<{
  id: VehicleId;
  label: Record<BookingLocale, string>;
  hint: Record<BookingLocale, string>;
}> = [
  { id: "sedan_suv", label: { en: "Car", fr: "Auto" }, hint: { en: "Bags, boxes", fr: "Sacs, boîtes" } },
  { id: "cargo_van", label: { en: "Van", fr: "Fourgon" }, hint: { en: "Cartons, parts", fr: "Cartons, pièces" } },
  { id: "box_16", label: { en: "Truck", fr: "Camion" }, hint: { en: "Pallets, bulky", fr: "Palettes, volumineux" } },
];

export interface BookingAddress {
  formatted: string;
  postal?: string;
  lat?: number;
  lng?: number;
  place_id?: string;
}

export interface BookingDraft {
  pickup: string;
  /** Drop-offs in visiting order. The last one is the final drop-off. 1..MAX_DROPS. */
  drops: string[];
  vehicle: VehicleId;
  name: string;
  email: string;
  phone: string;
}

export interface QuoteInput {
  pickup: BookingAddress;
  dropoff: BookingAddress;
  additional_stops?: BookingAddress[];
  vehicle_class: VehicleId;
  scheduled_at: string;
}

const POSTAL = /[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d/;
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/;

export function postalOf(text: string): string | undefined {
  const m = (text || "").match(POSTAL);
  if (!m) return undefined;
  const raw = m[0].toUpperCase().replace(/[ -]/g, "");
  return `${raw.slice(0, 3)} ${raw.slice(3)}`;
}

export function isAddress(text: string): boolean {
  const t = (text || "").trim();
  return t.length >= 8 && Boolean(postalOf(t));
}

export function isEmail(text: string): boolean {
  return EMAIL.test((text || "").trim());
}

export function isPhone(text: string): boolean {
  return (text || "").replace(/\D/g, "").length >= 10;
}

export function isVehicle(id: string | undefined | null): id is VehicleId {
  return BOOKING_VEHICLES.some((v) => v.id === id);
}

export function toAddress(text: string): BookingAddress {
  const formatted = (text || "").trim();
  return { formatted, postal: postalOf(formatted) };
}

/** Normalise drops: trim, drop blanks, cap at MAX_DROPS. */
export function cleanDrops(drops: string[]): string[] {
  return drops.map((d) => (d || "").trim()).filter(Boolean).slice(0, MAX_DROPS);
}

export function canAddDrop(drops: string[]): boolean {
  return drops.length < MAX_DROPS;
}

/** Quote payload or null when the trip is not complete yet. */
export function buildQuoteInput(
  draft: Pick<BookingDraft, "pickup" | "drops" | "vehicle">,
  now: number = Date.now()
): QuoteInput | null {
  const drops = cleanDrops(draft.drops);
  if (!isAddress(draft.pickup) || drops.length === 0 || !drops.every(isAddress)) return null;
  const final = drops[drops.length - 1];
  const extra = drops.slice(0, -1);
  return {
    pickup: toAddress(draft.pickup),
    dropoff: toAddress(final),
    ...(extra.length ? { additional_stops: extra.map(toAddress) } : {}),
    vehicle_class: draft.vehicle,
    scheduled_at: new Date(now + 5 * 60_000).toISOString(),
  };
}

export function contactOk(draft: Pick<BookingDraft, "name" | "email" | "phone">): boolean {
  return draft.name.trim().length > 1 && isEmail(draft.email) && isPhone(draft.phone);
}

export function formatPrice(cents: number, locale: BookingLocale = "en"): string {
  const v = (cents / 100).toFixed(2);
  return locale === "fr" ? `${v.replace(".", ",")} $` : `$${v}`;
}

export type BookingCopyKey = keyof typeof BOOKING_COPY.en;

export const BOOKING_COPY = {
  en: {
    eyebrow: "Same-day · Toronto & GTA",
    title: "Send it today.",
    lead: "No account. Price first. Pay with card, Apple Pay or Google Pay.",
    pickup: "Pickup",
    drop: "Drop-off",
    dropN: "Drop {n}",
    addDrop: "Add a drop",
    removeDrop: "Remove",
    dropsLimit: "Up to 5 drops per booking.",
    placeholder: "Street, city, postal code",
    vehicle: "Vehicle",
    name: "Your name",
    email: "Email",
    phone: "Phone",
    marketing: "Yes, PorterChain Logistics Inc. may email me delivery tips and offers. I can unsubscribe at any time.",
    optional: "(Optional)",
    pay: "Book & pay",
    paying: "Starting secure payment…",
    legal: "Incl. HST. By booking you agree to the Terms and Privacy Policy and confirm no dangerous goods.",
    terms: "Terms",
    privacy: "Privacy Policy",
    needTrip: "Add each address with its postal code to see your price.",
    needContact: "Add your name, email and phone so we can send your tracking link.",
    expired: "That price expired. Enter the trip again for a fresh price.",
    sameTrip: "Same trip as {ref}. Fresh price below.",
    loading: "Loading your trip…",
    changeTrip: "Change trip",
    recent: "Recent",
    payFailed: "Payment could not start. Try again.",
  },
  fr: {
    eyebrow: "Le jour même · Toronto et RGT",
    title: "Envoyez-le aujourd'hui.",
    lead: "Sans compte. Le prix d'abord. Payez par carte, Apple Pay ou Google Pay.",
    pickup: "Collecte",
    drop: "Livraison",
    dropN: "Livraison {n}",
    addDrop: "Ajouter une livraison",
    removeDrop: "Retirer",
    dropsLimit: "Jusqu'à 5 livraisons par réservation.",
    placeholder: "Rue, ville, code postal",
    vehicle: "Véhicule",
    name: "Votre nom",
    email: "Courriel",
    phone: "Téléphone",
    marketing: "Oui, PorterChain Logistics Inc. peut m'envoyer des conseils et des offres par courriel. Je peux me désabonner en tout temps.",
    optional: "(Facultatif)",
    pay: "Réserver et payer",
    paying: "Ouverture du paiement sécurisé…",
    legal: "TVH incluse. En réservant, vous acceptez les Conditions et la Politique de confidentialité et confirmez l'absence de marchandises dangereuses.",
    terms: "Conditions",
    privacy: "Politique de confidentialité",
    needTrip: "Ajoutez chaque adresse avec son code postal pour voir votre prix.",
    needContact: "Ajoutez votre nom, courriel et téléphone pour recevoir votre lien de suivi.",
    expired: "Ce prix a expiré. Entrez le trajet de nouveau pour un nouveau prix.",
    sameTrip: "Même trajet que {ref}. Nouveau prix ci-dessous.",
    loading: "Chargement de votre trajet…",
    changeTrip: "Modifier le trajet",
    recent: "Récentes",
    payFailed: "Le paiement n'a pas pu démarrer. Réessayez.",
  },
} as const;

export function bookingText(locale: BookingLocale, key: BookingCopyKey, vars: Record<string, string | number> = {}): string {
  const table = BOOKING_COPY[locale] ?? BOOKING_COPY.en;
  let text: string = table[key] ?? BOOKING_COPY.en[key];
  for (const [k, v] of Object.entries(vars)) text = text.replace(`{${k}}`, String(v));
  return text;
}

/** Which step blocks payment, in the order the customer sees it. */
export function payBlocker(
  draft: BookingDraft,
  hasPrice: boolean
): "needTrip" | "needContact" | null {
  if (!hasPrice) return "needTrip";
  if (!contactOk(draft)) return "needContact";
  return null;
}
