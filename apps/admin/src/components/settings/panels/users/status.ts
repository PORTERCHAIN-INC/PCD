import {
  ACCESS_STATUS_OPTIONS,
  CLERK_STATUS_OPTIONS,
  IDENTITY_STATUS_OPTIONS,
  INVITE_STATUS_OPTIONS,
} from "@/lib/settings";

export type BadgeTone = "green" | "amber" | "red" | "slate" | "sky";

export function accessTone(s: string): BadgeTone {
  if (s === "authorized") return "green";
  if (s === "pending_review" || s === "invite_pending") return "amber";
  if (s === "suspended" || s === "not_authorized" || s === "inactive" || s === "merchant_inactive")
    return "red";
  return "slate";
}

export function inviteTone(s: string): BadgeTone {
  if (s === "accepted") return "green";
  if (s === "invite_pending") return "amber";
  if (s === "not_invited") return "slate";
  if (s === "revoked" || s === "invite_failed") return "red";
  return "sky";
}

export function identityTone(
  s: string,
  opts?: { provisioned?: boolean; clerkLinked?: boolean }
): BadgeTone {
  if (opts?.provisioned === false) return "red";
  if (opts?.clerkLinked === false || s === "not_registered") return "red";
  if (s === "registered") return "green";
  if (s === "invite_pending") return "amber";
  return "slate";
}

export function labelFor(value: string, options: readonly { value: string; label: string }[]) {
  return options.find((o) => o.value === value)?.label ?? value.replace(/_/g, " ");
}

export function accessLabel(value: string) {
  return labelFor(value, ACCESS_STATUS_OPTIONS);
}

export function inviteLabel(value: string) {
  return labelFor(value, INVITE_STATUS_OPTIONS);
}

export function clerkLabel(
  clerkStatus: string | null | undefined,
  identityStatus: string,
  opts?: { provisioned?: boolean }
) {
  if (opts?.provisioned === false) return "Unprovisioned";
  if (identityStatus === "not_registered") return "Not in Clerk";
  if (clerkStatus) return labelFor(clerkStatus, CLERK_STATUS_OPTIONS);
  return labelFor(identityStatus, IDENTITY_STATUS_OPTIONS);
}
