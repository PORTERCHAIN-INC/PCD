import type { PodDraft } from "../ui/PodCapture";
import { emptyPodDraft } from "../ui/PodCapture";
import { deliverStop, podBarcode, podComplete, podIdCheck, podPhoto, podSignature } from "../api";
import { runOnlineOrQueue } from "../offline";
import type { PodRequirements } from "../types";

/**
 * Proof of delivery is required again (readiness audit #5). The API is the source of truth
 * (pod_policy + DRIVER_POD_ENFORCED); this mirrors it so the driver sees what is missing
 * before tapping Complete. A super admin can still finish a stop with an audited override.
 */
export const ENFORCE_DROP_POD = true;

/** Missing proof keys for the current draft (empty = ready). */
export function podMissing(
  draft: PodDraft,
  req: PodRequirements | null | undefined,
  otpRequired: boolean
): string[] {
  if (!ENFORCE_DROP_POD) return [];
  const enforced = req?.enforced ?? true;
  if (!enforced) return otpRequired && !draft.otp.trim() ? ["otp"] : [];
  const missing: string[] = [];
  const hasPhoto = Boolean(draft.photoUrl);
  const hasSignature = Boolean(draft.signature.trim());
  if (req?.photo && !hasPhoto) missing.push("photo");
  if (req?.signature && !hasSignature) missing.push("signature");
  if ((req?.photo_or_signature ?? true) && !hasPhoto && !hasSignature && !req?.signature) {
    missing.unshift("photo_or_signature");
  }
  if (req?.id_check && !(draft.idType && draft.idNameMatches)) missing.push("id_check");
  if (otpRequired && !draft.otp.trim()) missing.push("otp");
  return missing;
}

export const POD_MISSING_COPY: Record<string, string> = {
  photo_or_signature: "a photo or the receiver's signature",
  photo: "a delivery photo",
  signature: "the receiver's signature",
  id_check: "the receiver ID check",
  otp: "the receiver OTP",
};

type Args = {
  routeId: string | null;
  stopId: string | null;
  nextStopType: string | null | undefined;
  otpRequired: boolean;
  podRequirements?: PodRequirements | null;
  podDraft: PodDraft;
  setPodDraft: (next: PodDraft) => void;
};

/** Dropoff: send every captured proof, pod_complete, then deliver_stop. Pickup: deliver only. */
export async function completeStopAction({
  routeId,
  stopId,
  nextStopType,
  otpRequired,
  podRequirements,
  podDraft,
  setPodDraft,
}: Args): Promise<void> {
  if (!routeId || !stopId) throw new Error("no_stop");
  const needsPod = (nextStopType ?? "").toLowerCase() !== "pickup";

  if (needsPod) {
    const missing = podMissing(podDraft, podRequirements, otpRequired);
    if (missing.length) {
      throw new Error(
        `Capture ${missing.map((m) => POD_MISSING_COPY[m] ?? m).join(" and ")} before completing.`
      );
    }
  }

  const hasCapture =
    Boolean(podDraft.photoUrl) ||
    Boolean(podDraft.signature.trim()) ||
    Boolean(podDraft.barcode.trim()) ||
    Boolean(podDraft.idType && podDraft.idNameMatches);

  if (needsPod && hasCapture) {
    // Offline, each call is queued and the server replays them in order (proof, pod_complete,
    // then deliver_stop), so the gate is evaluated with the proof already recorded.
    try {
      if (podDraft.photoUrl) {
        await runOnlineOrQueue(
          "camera_upload",
          { stop_id: stopId, file_url: podDraft.photoUrl, route_id: routeId },
          () => podPhoto(routeId, stopId, podDraft.photoUrl as string)
        );
      }
      if (podDraft.signature.trim()) {
        await runOnlineOrQueue(
          "pod_signature",
          { stop_id: stopId, signature_data: podDraft.signature.trim(), route_id: routeId },
          () => podSignature(routeId, stopId, podDraft.signature.trim())
        );
      }
      if (podDraft.idType && podDraft.idNameMatches) {
        await runOnlineOrQueue(
          "pod_id_check",
          {
            stop_id: stopId,
            id_type: podDraft.idType,
            name_matches: true,
            route_id: routeId,
          },
          () => podIdCheck(routeId, stopId, { id_type: podDraft.idType, name_matches: true })
        );
      }
      if (podDraft.barcode.trim()) {
        await runOnlineOrQueue(
          "pod_barcode",
          { stop_id: stopId, barcode: podDraft.barcode.trim(), route_id: routeId },
          () => podBarcode(routeId, stopId, podDraft.barcode.trim())
        );
      }
      await runOnlineOrQueue(
        "pod_complete",
        { stop_id: stopId, otp: podDraft.otp.trim() || null, route_id: routeId },
        () => podComplete(routeId, stopId, podDraft.otp.trim() || undefined)
      );
    } catch (err) {
      if (ENFORCE_DROP_POD) throw err;
    }
  }

  await runOnlineOrQueue("deliver_stop", { stop_id: stopId, route_id: routeId }, () =>
    deliverStop(routeId, stopId)
  );
  setPodDraft(emptyPodDraft());
}
