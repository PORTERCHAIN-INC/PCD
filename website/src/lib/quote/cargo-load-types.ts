import type { CargoLoadType, QuoteItemInput } from "./types";

export const CARGO_LOAD_OPTIONS: {
  id: CargoLoadType;
  label: string;
  description: string;
}[] = [
  {
    id: "parcel",
    label: "Individual Parcel",
    description: "Boxes, envelopes, and single-piece freight with item dimensions.",
  },
  {
    id: "skid",
    label: "Skid",
    description: "Standard skid or pallet — weight and count; typical 48×40 in footprint.",
  },
  {
    id: "ltl",
    label: "LTL",
    description: "Less than truckload — partial trailer space across multiple units.",
  },
  {
    id: "ftl",
    label: "FTL",
    description: "Full truckload — exclusive use of a van or box truck.",
  },
];

/** Standard skid footprint in inches (matches quote form units). */
export const SKID_DEFAULT_DIMENSIONS_IN = {
  length: 48,
  width: 40,
  height: 60,
} as const;

export function buildQuoteItemsForCargoLoad(
  cargoLoadType: CargoLoadType,
  parcelItems: QuoteItemInput[],
  skidInput: { weightKg: number; quantity: number; heightIn?: number },
  ltlInput: {
    weightKg: number;
    quantity: number;
    lengthIn?: number;
    widthIn?: number;
    heightIn?: number;
  }
): QuoteItemInput[] {
  if (cargoLoadType === "parcel") {
    return parcelItems;
  }

  if (cargoLoadType === "skid") {
    return [
      {
        weight: skidInput.weightKg,
        length: SKID_DEFAULT_DIMENSIONS_IN.length,
        width: SKID_DEFAULT_DIMENSIONS_IN.width,
        height: skidInput.heightIn ?? SKID_DEFAULT_DIMENSIONS_IN.height,
        quantity: skidInput.quantity,
      },
    ];
  }

  if (cargoLoadType === "ltl") {
    return [
      {
        weight: ltlInput.weightKg,
        length: ltlInput.lengthIn ?? SKID_DEFAULT_DIMENSIONS_IN.length,
        width: ltlInput.widthIn ?? SKID_DEFAULT_DIMENSIONS_IN.width,
        height: ltlInput.heightIn ?? SKID_DEFAULT_DIMENSIONS_IN.height,
        quantity: ltlInput.quantity,
      },
    ];
  }

  return [];
}

export function cargoLoadTypeLabel(cargoLoadType: CargoLoadType): string {
  return CARGO_LOAD_OPTIONS.find((option) => option.id === cargoLoadType)?.label ?? cargoLoadType;
}
