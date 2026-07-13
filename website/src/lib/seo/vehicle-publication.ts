/**
 * W8b vehicle route index policy — buyer-facing B2B routes only (playbook §2.3).
 * Sedan/SUV remain noindex (consumer-adjacent); trade van, box truck, cargo van, pickup index when copy passes gate.
 */

export const INDEXABLE_VEHICLE_SEGMENTS = [
  "trade-van-delivery",
  "box-truck-delivery",
  "cargo-van-delivery",
  "pickup-truck-delivery",
] as const;

export type IndexableVehicleSegment = (typeof INDEXABLE_VEHICLE_SEGMENTS)[number];

const SEGMENT_TO_MESSAGE_KEY: Record<IndexableVehicleSegment, string> = {
  "trade-van-delivery": "van",
  "box-truck-delivery": "mediumTruck",
  "cargo-van-delivery": "cargoVan",
  "pickup-truck-delivery": "pickupTruck",
};

type VehicleCopy = {
  whenYouNeed?: string;
  whenYouNeedTitle?: string;
  useCases?: string;
  whoFor?: string;
};

export function isIndexableVehicleSegment(segment: string): segment is IndexableVehicleSegment {
  return (INDEXABLE_VEHICLE_SEGMENTS as readonly string[]).includes(segment);
}

export function getVehicleMessageKeyForSegment(segment: IndexableVehicleSegment): string {
  return SEGMENT_TO_MESSAGE_KEY[segment];
}

/** Minimum substantive copy before indexing (avoids thin doorway pages). */
export function isPublishableVehicleCopy(content: VehicleCopy | undefined): boolean {
  if (!content?.whenYouNeed || !content.useCases || !content.whoFor) return false;
  const total = content.whenYouNeed.length + content.useCases.length + content.whoFor.length;
  return total >= 200;
}

export function shouldIndexVehicleRoute(
  segment: string,
  messages: { vehicleDelivery?: Record<string, VehicleCopy> }
): boolean {
  if (!isIndexableVehicleSegment(segment)) return false;
  const key = getVehicleMessageKeyForSegment(segment);
  return isPublishableVehicleCopy(messages.vehicleDelivery?.[key]);
}
