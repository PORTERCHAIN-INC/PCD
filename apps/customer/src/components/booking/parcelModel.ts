import {
  CAPACITY_CLASS_LABELS,
  CAPACITY_CLASS_OPTIONS,
  type CapacityClassId,
} from "@porterchain/types";

export type BookingVehicle = {
  id: string;
  label: string;
  whole_vehicle_enabled?: boolean;
  allowed_presets?: string[] | null;
  included_km?: number | null;
  capacity_kg?: number | null;
  max_length_cm?: number | null;
  max_width_cm?: number | null;
  max_height_cm?: number | null;
};

export type BookingPreset = {
  id: string;
  label: string;
  manual?: boolean;
  length_in?: number | null;
  width_in?: number | null;
  height_in?: number | null;
  weight_lb?: number | null;
};

export type ParcelDraft = {
  preset_id: string;
  quantity: number;
  instructions: string;
  length_in: string;
  width_in: string;
  height_in: string;
  weight_lb: string;
};

const RETAIL_FALLBACK_IDS: CapacityClassId[] = [
  "sedan_suv",
  "pickup",
  "cargo_van",
  "box_16",
  "box_20",
];

export const FALLBACK_VEHICLES: BookingVehicle[] = RETAIL_FALLBACK_IDS.map((id) => {
  const row = CAPACITY_CLASS_OPTIONS.find((opt) => opt.id === id)!;
  return {
    id: row.id,
    label: CAPACITY_CLASS_LABELS[id],
    whole_vehicle_enabled: true,
    allowed_presets: id === "sedan_suv" ? ["small", "medium", "large", "other"] : null,
  };
});

export const FALLBACK_PRESETS: BookingPreset[] = [
  { id: "small", label: "Small" },
  { id: "medium", label: "Medium" },
  { id: "large", label: "Large" },
  { id: "extra_large", label: "Extra large" },
  { id: "skid", label: "Skid" },
  { id: "furniture", label: "Furniture" },
  { id: "other", label: "Other", manual: true },
];

const ALIASES: Record<string, string> = {
  sedan: "sedan_suv",
  suv: "sedan_suv",
  cargovan: "cargo_van",
  highroof: "sprinter_van",
  box16: "box_16",
  box20: "box_20",
  box_truck: "box_16",
};

export function canonicalVehicle(raw: string | null | undefined): string {
  const key = (raw ?? "").trim().toLowerCase().replace(/[\s-]/g, "_");
  return ALIASES[key] ?? ALIASES[key.replace(/_/g, "")] ?? key;
}

const IN_TO_CM = 2.54;
const LB_TO_KG = 0.45359237;

function pieceCm(draft: ParcelDraft, preset: BookingPreset | undefined) {
  const manual = preset?.manual || draft.preset_id === "other";
  const lengthIn = manual ? Number(draft.length_in) : Number(preset?.length_in);
  const widthIn = manual ? Number(draft.width_in) : Number(preset?.width_in);
  const heightIn = manual ? Number(draft.height_in) : Number(preset?.height_in);
  const weightLb = manual ? Number(draft.weight_lb) : Number(preset?.weight_lb);
  return {
    length: lengthIn * IN_TO_CM,
    width: widthIn * IN_TO_CM,
    height: heightIn * IN_TO_CM,
    weight: weightLb * LB_TO_KG,
  };
}

export function pieceFits(
  vehicle: BookingVehicle,
  draft: ParcelDraft,
  preset: BookingPreset | undefined
): boolean {
  const allowed = vehicle.allowed_presets;
  if (allowed?.length && !allowed.includes(draft.preset_id)) return false;
  const piece = pieceCm(draft, preset);
  if (
    ![piece.length, piece.width, piece.height, piece.weight].every(
      (n) => Number.isFinite(n) && n > 0
    )
  ) {
    return true;
  }
  const dims = [piece.length, piece.width, piece.height].sort((a, b) => b - a);
  const limits = [vehicle.max_length_cm, vehicle.max_width_cm, vehicle.max_height_cm]
    .map((n) => Number(n))
    .filter((n) => Number.isFinite(n) && n > 0)
    .sort((a, b) => b - a);
  if (limits.length === 3 && dims.some((side, index) => side > limits[index]!)) return false;
  return true;
}

export function nextFittingVehicle(
  vehicles: BookingVehicle[],
  drafts: ParcelDraft[],
  presets: BookingPreset[]
): BookingVehicle | null {
  return (
    vehicles.find((vehicle) =>
      drafts.every((draft) =>
        pieceFits(
          vehicle,
          draft,
          presets.find((preset) => preset.id === draft.preset_id)
        )
      )
    ) ?? null
  );
}

export function blankParcel(presetId = "small"): ParcelDraft {
  return {
    preset_id: presetId,
    quantity: 1,
    instructions: "",
    length_in: "",
    width_in: "",
    height_in: "",
    weight_lb: "",
  };
}

export function humanQuoteError(message: string): string {
  const known: Record<string, string> = {
    vehicle_rate_missing: "That vehicle has no customer price yet. Choose another.",
    vehicle_class_not_available: "That vehicle is not available. Choose another.",
    parcel_not_allowed: "That size is not allowed in a Sedan / SUV.",
    load_too_big: "This load is too big for the selected vehicle.",
    route_unavailable: "A road route is not available, so a price cannot be calculated yet.",
    quote_expired: "This price has expired. Save a new quote before paying.",
    parcels_required: "Add a parcel, or choose the whole vehicle.",
    whole_vehicle_not_available: "Whole vehicle is not offered for this class.",
    pickup_outside_service_area: "Pickup is outside the service area.",
    dropoff_outside_service_area: "Dropoff is outside the service area.",
  };
  if (known[message]) return known[message];
  if (message.startsWith("quote_price_changed:")) {
    const cents = Number(message.split(":")[1]);
    if (Number.isFinite(cents)) {
      const dollars = (cents / 100).toLocaleString("en-CA", {
        style: "currency",
        currency: "CAD",
      });
      return `The price updated to ${dollars}. Confirm again to pay the new amount.`;
    }
    return "The price changed. Confirm again to pay the new amount.";
  }
  return message;
}
