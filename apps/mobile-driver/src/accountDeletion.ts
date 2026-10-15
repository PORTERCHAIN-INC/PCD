/**
 * In-app account deletion (App Store Guideline 5.1.1(v)).
 * Files a tracked deletion request with ops; the account is deleted within the SLA,
 * keeping only delivery records the law requires.
 */
export const ACCOUNT_DELETION_NOTE = "Driver requested full account deletion from the app.";

export type PrivacyRequester = (
  kind: "access" | "correction" | "deletion",
  note?: string
) => Promise<{ status: string; reference: string | null; sla_days: number }>;

export async function requestAccountDeletion(
  request: PrivacyRequester
): Promise<{ title: string; body: string }> {
  const r = await request("deletion", ACCOUNT_DELETION_NOTE);
  const ref = r.reference ? `Reference ${r.reference}. ` : "";
  return {
    title: "Deletion requested",
    body: `${ref}Your account and personal data will be deleted within ${r.sla_days} days. Delivery records the law requires are kept.`,
  };
}
