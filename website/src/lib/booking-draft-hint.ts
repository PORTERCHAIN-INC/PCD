const HINT_KEY = "pc_booking_draft_hint";

/** Set after the visitor starts a booking (server draft created). */
export function markBookingDraftHint(): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.setItem(HINT_KEY, "1");
}

export function clearBookingDraftHint(): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.removeItem(HINT_KEY);
}

/** True when we should check the API for an in-progress booking draft. */
export function hasBookingDraftHint(): boolean {
  if (typeof sessionStorage === "undefined") return false;
  return sessionStorage.getItem(HINT_KEY) === "1";
}
