/**
 * First-run copy for a waiting merchant seat (AY).
 *
 * The status glossary is injected so this module stays import-free and the words
 * always come from the shared catalog — the same nouns admin uses (AP).
 */
import type { PortalOnboardingStatus } from "@/lib/onboarding";

export type StatusLabeller = (status: string | null | undefined) => string;

/** What this seat is actually waiting on: its own seat, the owner, or PorterChain. */
export function waitCopy(data: PortalOnboardingStatus, statusLabel: StatusLabeller): string {
  const label = data.status_label || statusLabel(data.status);
  const blockers = data.blockers ?? [];

  if (blockers.includes("merchant_provisioned")) {
    return "This email does not have a seat yet. Ask your owner to add it on the Team page, then sign in again.";
  }
  if (blockers.includes("team_access")) {
    return "Your seat is turned off. Ask your owner to turn it back on.";
  }
  if (data.status === "SUSPENDED") {
    return `This company is ${label}. Contact PorterChain to restore access.`;
  }
  if (data.status === "CLOSED") {
    return `This company is ${label}. Sign in with another company or contact PorterChain.`;
  }
  if (data.status === "ONBOARDING" || data.status === "PENDING") {
    const wait = `PorterChain is reviewing this company. Status is ${label} until we activate it. Bookings stay locked until ${statusLabel("ACTIVE")}.`;
    return data.can_edit_company
      ? `${wait} You can finish the company file while you wait.`
      : `${wait} Your owner finishes the company file.`;
  }
  return `Your dashboard opens when this company is ${statusLabel("ACTIVE")}.`;
}

/** Only nag about the company file when it is incomplete and this seat cannot fix it. */
export function askOwnerForCompanyFile(data: PortalOnboardingStatus): boolean {
  if (data.can_edit_company) return false;
  if ((data.blockers ?? []).some((b) => b === "merchant_provisioned" || b === "team_access")) {
    return false;
  }
  return data.completeness?.complete === false;
}
