import type { PodRequirements } from "../types";
import type { PodDraft } from "./podDraft";

export type PodNeed = "photo_or_signature" | "photo" | "signature" | "id_check" | "otp";

/**
 * Missing proof for the current draft (empty = ready), in the order the driver should do it.
 * Mirrors the server's pod_policy.missing_for(); the server's pod_requirements are the only
 * source of truth. Before the server has answered (null), use the server default
 * (photo or signature) so the app never says "ready" and then gets rejected.
 */
export function podMissing(
  draft: PodDraft,
  req: PodRequirements | null | undefined,
  otpRequired: boolean
): PodNeed[] {
  const policy: PodRequirements = req ?? { enforced: true, photo_or_signature: true };
  const needOtp = otpRequired || Boolean(policy.otp);
  const otpMissing = needOtp && !draft.otp.trim();
  if (policy.enforced === false) return otpMissing ? ["otp"] : [];
  const hasPhoto = Boolean(draft.photoUrl);
  const hasSignature = Boolean(draft.signature.trim());
  const missing: PodNeed[] = [];
  if (policy.photo && !hasPhoto) missing.push("photo");
  if (policy.signature && !hasSignature) missing.push("signature");
  if (policy.photo_or_signature && !hasPhoto && !hasSignature && !missing.includes("signature")) {
    missing.unshift("photo_or_signature");
  }
  if (policy.id_check && !(draft.idType && draft.idNameMatches)) missing.push("id_check");
  if (otpMissing) missing.push("otp");
  return missing;
}

export const POD_NEED_COPY: Record<PodNeed, string> = {
  photo_or_signature: "a photo or the receiver's signature",
  photo: "a delivery photo",
  signature: "the receiver's signature",
  id_check: "the receiver ID check",
  otp: "the receiver's code",
};
