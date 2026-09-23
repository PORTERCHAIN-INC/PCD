const COPY: Record<string, string> = {
  signed_out: "Sign in to continue.",
  email_required: "Add a verified email in Clerk, then try again.",
  email_clerk_mismatch: "This email is linked to a different Porterchain account.",
  user_not_provisioned: "This account is not provisioned for the customer portal.",
  missing_portal_permission: "This account is not provisioned for the customer portal.",
  booking_self_service_disabled: "Booking is turned off. You can still track a shipment.",
  vehicle_class_not_available: "That vehicle is not enabled. Choose another.",
  vehicle_rate_missing: "That vehicle has no customer price yet. Choose another.",
  parcel_not_allowed: "That size is not allowed in a Sedan / SUV.",
  load_too_big: "This load is too big for the selected vehicle.",
  route_unavailable: "A road route is not available, so a price cannot be calculated yet.",
  quote_expired: "This price has expired. Get a new quote before paying.",
  parcels_required: "Add a parcel, or choose the whole vehicle.",
  whole_vehicle_not_available: "Whole vehicle is not offered for this class.",
  pickup_outside_service_area: "That pickup is outside the service area.",
  quote_not_found: "This quote expired. Get a new quote.",
  order_not_found: "Shipment not found.",
  mock_checkout_disabled: "Test checkout is not available on this server.",
  checkout_unavailable: "Porterchain did not return a payment link.",
  payment_failed: "Payment did not complete. Retry from Activity.",
  payment_still_processing: "Payment may still be confirming. Check Activity in a few minutes.",
  clerk_user_mismatch: "Sign in again, then retry the booking.",
  http_401: "Sign in again to continue.",
  http_403: "Porterchain refused this request.",
  request_failed: "Porterchain could not complete that request.",
};

export function humanCustomerError(raw: string): string {
  const key = raw.trim();
  if (COPY[key]) return COPY[key];
  if (key.startsWith("identity_conflict")) {
    return "This sign-in is a staff, merchant, or driver account. Sign out and use a customer account.";
  }
  if (key.startsWith("http_")) return `Porterchain returned ${key.replace("http_", "")}.`;
  return key.replace(/_/g, " ");
}
