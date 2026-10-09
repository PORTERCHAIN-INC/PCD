/** Public tracking: collapse the order state machine into five steps a receiver understands. */
export const TRACK_STEPS = ["booked", "assigned", "pickedUp", "onTheWay", "delivered"] as const;
export type TrackStep = (typeof TRACK_STEPS)[number];

export type TrackStatus = { kind: "progress"; step: number } | { kind: "exception"; state: string };

const STEP_OF: Record<string, number> = {
  BOOKED: 0,
  DISPATCH_READY: 0,
  DRIVER_REJECTED: 0,
  DRIVER_ASSIGNED: 1,
  DRIVER_ACCEPTED: 1,
  DRIVER_EN_ROUTE: 1,
  AT_PICKUP: 1,
  PICKED_UP: 2,
  IN_TRANSIT: 3,
  AT_DESTINATION: 3,
  DELIVERED: 4,
  POD_COMPLETED: 4,
  INVOICED: 4,
  CLOSED: 4,
};

export function trackStatus(state: string | null | undefined, delivered = false): TrackStatus {
  if (delivered) return { kind: "progress", step: 4 };
  const s = (state ?? "").toUpperCase();
  if (s in STEP_OF) return { kind: "progress", step: STEP_OF[s]! };
  if (!s) return { kind: "progress", step: 0 };
  return { kind: "exception", state: s };
}
