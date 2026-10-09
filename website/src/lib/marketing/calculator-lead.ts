/**
 * Price-calculator lead magnet — pure helpers (no imports so `node --test` can load it).
 */

export const CALCULATOR_VEHICLES = [
  { id: "sedan_suv", label: "Sedan / SUV", hint: "Bags, totes, small boxes" },
  { id: "cargo_van", label: "Cargo van", hint: "Cartons, parts, small pallets" },
  { id: "box_16", label: "16 ft box truck", hint: "Pallets and bulky freight" },
] as const;

export type CalculatorVehicle = (typeof CALCULATOR_VEHICLES)[number]["id"];

export const CALCULATOR_INDUSTRIES = [
  { id: "shopify-merchants", label: "Shopify / e-commerce" },
  { id: "pharmacy", label: "Pharmacy" },
  { id: "labs", label: "Lab / specimens" },
  { id: "warehouses", label: "Warehouse / 3PL" },
  { id: "wholesale-traders", label: "Wholesale / trading" },
  { id: "construction", label: "Construction" },
  { id: "plumbing-electrical", label: "Plumbing / electrical parts" },
  { id: "other", label: "Other" },
] as const;

export const MONTHLY_VOLUMES = ["1-20", "21-100", "101-500", "500+"] as const;

/** Uppercase FSA ("M5V") from any postal-code input, or "" when it is not one. */
export function normalizeFsa(input: string | null | undefined): string {
  const value = (input ?? "").toUpperCase().replace(/\s+/g, "");
  return /^[A-Z]\d[A-Z]/.test(value) ? value.slice(0, 3) : "";
}

export function isCalculatorVehicle(value: string | null | undefined): value is CalculatorVehicle {
  return CALCULATOR_VEHICLES.some((v) => v.id === value);
}

export function isCalculatorIndustry(value: string | null | undefined): boolean {
  return CALCULATOR_INDUSTRIES.some((i) => i.id === value);
}

export type LeadForm = {
  businessName: string;
  email: string;
  phone: string;
  industry: string;
  monthlyVolume: string;
  /** Separate CASL box — must start unchecked. */
  marketingConsent: boolean;
  /** Honeypot; hidden from people. */
  website: string;
};

export const EMPTY_LEAD_FORM: LeadForm = {
  businessName: "",
  email: "",
  phone: "",
  industry: "",
  monthlyVolume: "",
  marketingConsent: false,
  website: "",
};

export type LeadErrors = Partial<Record<keyof LeadForm, string>>;

export function validateLeadForm(form: LeadForm): LeadErrors {
  const errors: LeadErrors = {};
  if (!form.businessName.trim()) errors.businessName = "Enter your business name.";
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(form.email.trim())) {
    errors.email = "Enter a valid email address.";
  }
  if ((form.phone.match(/\d/g) ?? []).length < 10) errors.phone = "Enter a 10-digit phone number.";
  if (!isCalculatorIndustry(form.industry)) errors.industry = "Pick your industry.";
  if (!(MONTHLY_VOLUMES as readonly string[]).includes(form.monthlyVolume)) {
    errors.monthlyVolume = "Pick a monthly volume.";
  }
  return errors;
}

export type LeadAttribution = {
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_term?: string;
  utm_content?: string;
  landingPageUrl?: string;
  referrer?: string;
  sourcePage?: string;
};

export type EstimateSnapshot = {
  pickupFsa: string;
  dropoffFsa: string;
  vehicle: string;
  amountCents: number;
};

/** Body for POST /v1/public/calculator-leads (snake_case API contract). */
export function buildLeadPayload(input: {
  form: LeadForm;
  attribution: LeadAttribution;
  estimate?: EstimateSnapshot | null;
  visitorId?: string;
  heroVariant?: string;
  formElapsedMs: number;
}): Record<string, string | number | boolean | undefined> {
  const { form, attribution: a, estimate } = input;
  return {
    business_name: form.businessName.trim(),
    email: form.email.trim(),
    phone: form.phone.trim(),
    industry: form.industry,
    monthly_volume: form.monthlyVolume,
    marketing_consent: form.marketingConsent === true,
    website: form.website,
    form_elapsed_ms: Math.max(0, Math.round(input.formElapsedMs)),
    pickup_fsa: estimate?.pickupFsa,
    dropoff_fsa: estimate?.dropoffFsa,
    vehicle_class: estimate?.vehicle,
    estimate_cents: estimate?.amountCents,
    utm_source: a.utm_source,
    utm_medium: a.utm_medium,
    utm_campaign: a.utm_campaign,
    utm_term: a.utm_term,
    utm_content: a.utm_content,
    landing_page: a.landingPageUrl,
    referrer: a.referrer,
    source_page: a.sourcePage,
    visitor_id: input.visitorId,
    hero_variant: input.heroVariant,
  };
}

export function formatCad(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}

// ---------------------------------------------------------------- A/B flag

/** Stable 0-99 bucket from a visitor id (FNV-1a). */
export function bucketOf(seed: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < seed.length; i += 1) {
    h ^= seed.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0) % 100;
}

export type HeroAbConfig = { enabled: boolean; experiment: string; split_percent: number };

/** "control" unless the flag is on and the visitor's bucket falls in the split. */
export function assignHeroVariant(
  config: HeroAbConfig | null | undefined,
  seed: string
): "control" | "b" {
  if (!config?.enabled) return "control";
  const split = Math.min(100, Math.max(0, Math.round(config.split_percent)));
  return bucketOf(`${config.experiment}:${seed}`) < split ? "b" : "control";
}
