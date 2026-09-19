import type { PodDraft } from "../ui/PodCapture";
import { emptyPodDraft } from "../ui/PodCapture";
import { deliverStop, podBarcode, podComplete, podPhoto, podSignature } from "../api";
import { runOnlineOrQueue } from "../offline";

type Args = {
  routeId: string | null;
  stopId: string | null;
  nextStopType: string | null | undefined;
  otpRequired: boolean;
  podDraft: PodDraft;
  setPodDraft: (next: PodDraft) => void;
};

/** Dropoff: photo (+ OTP when required) then deliver_stop. Pickup: deliver only. */
export async function completeStopAction({
  routeId,
  stopId,
  nextStopType,
  otpRequired,
  podDraft,
  setPodDraft,
}: Args): Promise<void> {
  if (!routeId || !stopId) throw new Error("no_stop");
  const needsPod = (nextStopType ?? "").toLowerCase() !== "pickup";

  if (needsPod) {
    if (!podDraft.photoUrl) throw new Error("photo_required");
    if (otpRequired && !podDraft.otp.trim()) throw new Error("otp_required");
    const mode = await runOnlineOrQueue(
      "camera_upload",
      { stop_id: stopId, file_url: podDraft.photoUrl, route_id: routeId },
      () => podPhoto(routeId, stopId, podDraft.photoUrl as string)
    );
    if (podDraft.signature.trim()) {
      await runOnlineOrQueue(
        "pod_signature",
        {
          stop_id: stopId,
          signature_data: podDraft.signature.trim(),
          route_id: routeId,
        },
        () => podSignature(routeId, stopId, podDraft.signature.trim())
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
    if (mode === "queued") {
      setPodDraft(emptyPodDraft());
      return;
    }
  }

  await runOnlineOrQueue("deliver_stop", { stop_id: stopId, route_id: routeId }, () =>
    deliverStop(routeId, stopId)
  );
  setPodDraft(emptyPodDraft());
}
