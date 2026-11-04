/** L97: when ops may hand an order to a courier / contractor fleet partner. */
export const PARTNER_ASSIGNABLE = new Set(["BOOKED", "DISPATCH_READY", "DRIVER_REJECTED"]);
export const COURIER_KINDS = new Set(["courier", "3pl"]);

export type CourierLegLite = { status: string };

export function openCourierLeg<T extends CourierLegLite>(legs: T[]): T | undefined {
  return legs.find((l) => l.status !== "delivered" && l.status !== "cancelled");
}

export function canAssignPartner(
  state: string | null | undefined,
  hasDriver: boolean,
  legs: CourierLegLite[]
): boolean {
  return !openCourierLeg(legs) && !hasDriver && PARTNER_ASSIGNABLE.has(String(state || ""));
}
