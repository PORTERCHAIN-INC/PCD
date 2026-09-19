/** English words. API IDs stay camelCase / SCREAMING_SNAKE. Same glossary as the merchant portal. */

const MERCHANT_STATUS_LABELS: Record<string, string> = {
  PENDING: "Pending",
  ONBOARDING: "Onboarding",
  ACTIVE: "Active",
  SUSPENDED: "Suspended",
  CLOSED: "Closed",
};

const ONBOARDING_PHASE_LABELS: Record<string, string> = {
  ready: "Portal ready",
  needs_invite: "Needs invite",
  awaiting_clerk: "Awaiting sign-in",
  needs_activation: "User inactive",
  needs_approval: "Needs approval",
  onboarding: "Onboarding",
};

const SEAT_STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  active: "Active",
  off: "Off",
};

const INVITE_STATUS_LABELS: Record<string, string> = {
  accepted: "Accepted",
  invite_pending: "Invite pending",
  not_invited: "Not invited",
  invite_failed: "Invite failed",
  revoked: "Revoked",
};

function pretty(key: string): string {
  const text = key.replace(/_/g, " ").trim();
  if (!text) return "—";
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function lookup(map: Record<string, string>, key: string | null | undefined): string {
  if (!key) return "—";
  return map[key] || map[key.toLowerCase()] || pretty(key);
}

export function merchantStatusLabel(status: string | null | undefined): string {
  if (!status) return "Unknown";
  return (
    MERCHANT_STATUS_LABELS[status] || MERCHANT_STATUS_LABELS[status.toUpperCase()] || pretty(status)
  );
}

export function onboardingPhaseLabel(phase: string | null | undefined): string {
  return lookup(ONBOARDING_PHASE_LABELS, phase);
}

export function seatStatusLabel(status: string | null | undefined): string {
  return lookup(SEAT_STATUS_LABELS, status);
}

export function inviteStatusLabel(status: string | null | undefined): string {
  return lookup(INVITE_STATUS_LABELS, status);
}
