import { DimensionUnit, WeightUnit, type LegacyParcelSerialization, type Parcel } from "./types";

/** Industry domestic volumetric divisor: cm³ / 5000 = kg. */
export const VOLUMETRIC_DIVISOR_CM = 5000;

const KG_PER_LB = 0.45359237;
const CM_PER_IN = 2.54;
const CM_PER_FT = 30.48;

function assertFiniteNonNegative(value: number, label: string): void {
  if (!Number.isFinite(value) || value < 0) {
    throw new Error(`${label} must be a non-negative number`);
  }
}

function round3(value: number): number {
  return Math.round(value * 1000) / 1000;
}

export function convertToKg(weight: number, fromUnit: WeightUnit): number {
  assertFiniteNonNegative(weight, "weight");
  if (fromUnit === WeightUnit.KG) return round3(weight);
  if (fromUnit === WeightUnit.LBS) return round3(weight * KG_PER_LB);
  throw new Error(`Unsupported weight unit: ${String(fromUnit)}`);
}

export function convertToCm(value: number, fromUnit: DimensionUnit): number {
  assertFiniteNonNegative(value, "dimension");
  if (fromUnit === DimensionUnit.CM) return round3(value);
  if (fromUnit === DimensionUnit.IN) return round3(value * CM_PER_IN);
  if (fromUnit === DimensionUnit.FT) return round3(value * CM_PER_FT);
  throw new Error(`Unsupported dimension unit: ${String(fromUnit)}`);
}

/**
 * Volumetric weight in kilograms. Dimensions are converted to centimetres
 * before applying the 5000 divisor so inches and feet are not treated as cm.
 */
export function calculateVolumetricWeight(
  length: number,
  width: number,
  height: number,
  unit: DimensionUnit
): number {
  const cubicCm = convertToCm(length, unit) * convertToCm(width, unit) * convertToCm(height, unit);
  return round3(cubicCm / VOLUMETRIC_DIVISOR_CM);
}

export function chargeableWeightKg(parcel: Parcel): number {
  const actual = convertToKg(parcel.weight, parcel.weightUnit);
  const volumetric =
    parcel.volumetricWeightKg > 0
      ? parcel.volumetricWeightKg
      : calculateVolumetricWeight(
          parcel.length,
          parcel.width,
          parcel.height,
          parcel.dimensionsUnit
        );
  return round3(Math.max(actual, volumetric));
}

export function withVolumetricWeight(parcel: Omit<Parcel, "volumetricWeightKg">): Parcel {
  try {
    return {
      ...parcel,
      volumetricWeightKg: calculateVolumetricWeight(
        parcel.length,
        parcel.width,
        parcel.height,
        parcel.dimensionsUnit
      ),
    };
  } catch {
    return { ...parcel, volumetricWeightKg: 0 };
  }
}

/**
 * Flatten parcels onto the legacy booking fields.
 * weight_kg is the sum of actual mass (not chargeable/volumetric).
 * dimensions groups identical specs, e.g. `2x [12x12x12 in, 5 lbs]`.
 */
export function serializeParcelsForLegacyAPI(parcels: Parcel[]): LegacyParcelSerialization {
  if (parcels.length === 0) {
    return { weight_kg: 0, dimensions: "" };
  }

  let totalKg = 0;
  const groups = new Map<string, number>();

  for (const parcel of parcels) {
    totalKg += convertToKg(parcel.weight, parcel.weightUnit);
    const spec = formatParcelSpec(parcel);
    groups.set(spec, (groups.get(spec) ?? 0) + 1);
  }

  const dimensions = [...groups.entries()]
    .map(([spec, count]) => `${count}x [${spec}]`)
    .join(" | ");

  return { weight_kg: round3(totalKg), dimensions };
}

export function formatParcelSpec(parcel: Parcel): string {
  const l = trimNumber(parcel.length);
  const w = trimNumber(parcel.width);
  const h = trimNumber(parcel.height);
  const weight = trimNumber(parcel.weight);
  return `${l}x${w}x${h} ${parcel.dimensionsUnit}, ${weight} ${parcel.weightUnit}`;
}

function trimNumber(value: number): string {
  if (!Number.isFinite(value)) return "0";
  return String(round3(value));
}

export function sumActualWeightKg(parcels: Parcel[]): number {
  return round3(
    parcels.reduce((sum, parcel) => sum + convertToKg(parcel.weight, parcel.weightUnit), 0)
  );
}

export function sumChargeableWeightKg(parcels: Parcel[]): number {
  return round3(parcels.reduce((sum, parcel) => sum + chargeableWeightKg(parcel), 0));
}

export function parcelVolumeCm3(parcel: Parcel): number {
  return round3(
    convertToCm(parcel.length, parcel.dimensionsUnit) *
      convertToCm(parcel.width, parcel.dimensionsUnit) *
      convertToCm(parcel.height, parcel.dimensionsUnit)
  );
}
