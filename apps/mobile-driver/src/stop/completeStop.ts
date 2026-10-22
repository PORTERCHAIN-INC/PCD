import { deliverStop, podComplete, podIdCheck, podPhoto, podSignature } from "../api";
import { runOnlineOrQueue } from "../offline";
import type { PodRequirements } from "../types";
import type { PodDraft } from "./podDraft";
import { POD_NEED_COPY, podMissing } from "./podRules";

type Args = {
  routeId: string | null;
  stopId: string | null;
  kind: "pickup" | "delivery" | null;
  otpRequired: boolean;
  podRequirements?: PodRequirements | null;
  pod: PodDraft;
  /** Middle drop of a multi-stop order: its own proof, no pod_complete (that closes the order). */
  midStop?: boolean;
};

/**
 * Pickup: deliver_stop only. Delivery: each captured proof, pod_complete, then deliver_stop.
 * A server rejection (4xx) throws to the driver. Only "no connection" queues, and once one
 * call is queued the rest queue behind it, so the server replays proof → pod_complete →
 * deliver_stop in order. Returns "queued" when the stop is saved on the phone to sync later.
 */
export async function completeStop({
  routeId,
  stopId,
  kind,
  otpRequired,
  podRequirements,
  pod,
  midStop = false,
}: Args): Promise<"online" | "queued"> {
  if (!routeId || !stopId) throw new Error("no_stop");
  const ids = { stop_id: stopId, route_id: routeId };

  if (kind === "delivery") {
    const missing = podMissing(pod, podRequirements, otpRequired);
    if (missing.length) {
      throw new Error(`Add ${missing.map((m) => POD_NEED_COPY[m]).join(" and ")} first.`);
    }
    const signature = pod.signature.trim();
    const otp = pod.otp.trim();
    if (pod.photoUrl) {
      const photo = pod.photoUrl;
      await runOnlineOrQueue("camera_upload", { ...ids, file_url: photo }, () =>
        podPhoto(routeId, stopId, photo)
      );
    }
    if (signature) {
      await runOnlineOrQueue("pod_signature", { ...ids, signature_data: signature }, () =>
        podSignature(routeId, stopId, signature)
      );
    }
    if (midStop) {
      return runOnlineOrQueue("deliver_stop", ids, () => deliverStop(routeId, stopId));
    }
    if (pod.idType && pod.idNameMatches) {
      await runOnlineOrQueue(
        "pod_id_check",
        { ...ids, id_type: pod.idType, name_matches: true },
        () => podIdCheck(routeId, stopId, { id_type: pod.idType, name_matches: true })
      );
    }
    await runOnlineOrQueue("pod_complete", { ...ids, otp: otp || null }, () =>
      podComplete(routeId, stopId, otp || undefined)
    );
  }

  return runOnlineOrQueue("deliver_stop", ids, () => deliverStop(routeId, stopId));
}
