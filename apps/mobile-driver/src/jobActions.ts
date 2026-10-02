/** Which buttons a driver may see for an order. One rule for the home screen, job list, and job screen. */

export function jobState(
  job: { state?: string | null; status?: string | null } | null | undefined
): string {
  return (job?.state || job?.status || "").trim().toUpperCase();
}

/** Dispatch is still waiting for Accept or Decline. */
export function jobNeedsAccept(
  job: { state?: string | null; status?: string | null } | null | undefined
): boolean {
  return jobState(job) === "DRIVER_ASSIGNED";
}

const PICKUP_WORK = new Set(["DRIVER_ACCEPTED", "DRIVER_EN_ROUTE", "AT_PICKUP"]);
const DELIVERY_WORK = new Set(["PICKED_UP", "IN_TRANSIT", "AT_DESTINATION"]);
const ARRIVE_PICKUP = new Set(["DRIVER_ACCEPTED", "DRIVER_EN_ROUTE"]);
const ARRIVE_DELIVERY = new Set(["PICKED_UP", "IN_TRANSIT"]);

/** Accepted through the delivery stop. Accept and Decline are already done. */
export function jobInProgress(
  job: { state?: string | null; status?: string | null } | null | undefined
): boolean {
  const state = jobState(job);
  return PICKUP_WORK.has(state) || DELIVERY_WORK.has(state);
}

export function isDeliveryStop(stopType: string | null | undefined): boolean {
  const stop = (stopType || "").trim().toLowerCase();
  return stop === "delivery" || stop === "dropoff" || stop === "drop_off";
}

export type StopWork = {
  arrive: boolean;
  complete: boolean;
};

/** Arrive and complete follow the order state and the stop in front of the driver. */
export function stopWork(
  state: string | null | undefined,
  stopType: string | null | undefined
): StopWork {
  const current = (state || "").trim().toUpperCase();
  const stop = (stopType || "").trim().toLowerCase();
  if (!current || !stop) return { arrive: false, complete: false };
  if (isDeliveryStop(stop)) {
    return { arrive: ARRIVE_DELIVERY.has(current), complete: DELIVERY_WORK.has(current) };
  }
  if (stop === "pickup") {
    return { arrive: ARRIVE_PICKUP.has(current), complete: PICKUP_WORK.has(current) };
  }
  return { arrive: false, complete: false };
}
