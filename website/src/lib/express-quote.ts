/**
 * Public express quote = parcel pricing. Hourly whole-vehicle pricing is merchants only
 * (Ravi 2026-10-31; API returns 400 whole_vehicle_merchants_only for booking_mode "vehicle").
 * Rate card: small parcel $6, van-size parcel $9 (+HST); the API price is authoritative.
 */
export type ParcelSize = "small" | "van";

export const PARCEL_SIZES: ReadonlyArray<{
  id: ParcelSize;
  presetId: "small" | "large";
  label: Record<"en" | "fr", string>;
  hint: Record<"en" | "fr", string>;
}> = [
  {
    id: "small",
    presetId: "small",
    label: { en: "Small parcel", fr: "Petit colis" },
    hint: { en: "Envelopes, bags, small boxes", fr: "Enveloppes, sacs, petites boîtes" },
  },
  {
    id: "van",
    presetId: "large",
    label: { en: "Van-size parcel", fr: "Colis format fourgon" },
    hint: { en: "Cartons, bulky items", fr: "Cartons, articles volumineux" },
  },
];

export const PARCEL_SIZE_LEGEND = { en: "Parcel size", fr: "Taille du colis" } as const;

export function isParcelSize(v: string | undefined | null): v is ParcelSize {
  return PARCEL_SIZES.some((s) => s.id === v);
}

/** Old links carried ?vehicle=cargo_van|box_16; map them to the van-size parcel. */
export function parcelSizeFromLink(v: string | undefined | null): ParcelSize {
  if (isParcelSize(v)) return v;
  return v === "cargo_van" || v === "box_16" ? "van" : "small";
}

export function parcelPresetId(size: ParcelSize | undefined): "small" | "large" {
  return PARCEL_SIZES.find((s) => s.id === size)?.presetId ?? "small";
}

/** JSON body for /v1/quotes and /v1/quotes/preview. Never sends booking_mode "vehicle". */
export function expressQuoteBody<T extends { parcel_size?: ParcelSize }>(input: T): string {
  const { parcel_size, ...rest } = input;
  return JSON.stringify({
    ...rest,
    booking_mode: "parcels",
    parcels: [{ preset_id: parcelPresetId(parcel_size), quantity: 1 }],
    schedule_mode: "now",
  });
}
