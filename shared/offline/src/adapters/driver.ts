import type { DriverApi } from "@porterchain/mobile-api";
import type { OfflineSyncAdapter } from "@porterchain/mobile-api";

export function createDriverOfflineSyncAdapter(api: DriverApi): OfflineSyncAdapter {
  return {
    queueAction: (actionType, payload, clientId) => api.queueOffline(actionType, payload, clientId),
    sync: () => api.syncOffline(),
    retryFailed: () => api.retryOffline(),
    getStatus: () => api.offlineStatus(),
    uploadFile: async (localUri) => {
      if (localUri.startsWith("http://") || localUri.startsWith("https://")) return localUri;
      return `https://cdn.porterchain.local/uploads/${encodeURIComponent(localUri.split("/").pop() ?? "file")}`;
    },
    executeDirect: async (actionType, payload) => {
      if (actionType === "accept_order" && payload.order_id) {
        return api.acceptOrder(String(payload.order_id));
      }
      if (actionType === "reject_order" && payload.order_id) {
        return api.rejectOrder(String(payload.order_id), String(payload.reason ?? ""));
      }
      if (actionType === "pod_complete" && payload.stop_id) {
        return api.podComplete(
          String(payload.route_id ?? ""),
          String(payload.stop_id),
          payload.otp ? String(payload.otp) : undefined
        );
      }
      if (actionType === "pod_photo" && payload.stop_id) {
        return api.podPhoto(
          String(payload.route_id ?? ""),
          String(payload.stop_id),
          String(payload.file_url ?? "")
        );
      }
      if (actionType === "pod_signature" && payload.stop_id) {
        return api.podSignature(
          String(payload.route_id ?? ""),
          String(payload.stop_id),
          String(payload.signature_data ?? "")
        );
      }
      if (actionType === "generate_otp" && payload.order_id) {
        return api.generateOtp(String(payload.order_id));
      }
      if (actionType === "otp_verify" && payload.order_id) {
        await api.queueOffline("otp_verify", payload);
        return api.syncOffline();
      }
      if (actionType === "location") {
        return api.postLocation({
          lat: Number(payload.lat),
          lng: Number(payload.lng),
          accuracy_m: payload.accuracy_m ? Number(payload.accuracy_m) : undefined,
          heading: payload.heading ? Number(payload.heading) : undefined,
          speed_mps: payload.speed_mps ? Number(payload.speed_mps) : undefined,
        });
      }
      return api.queueOffline(actionType, payload);
    },
  };
}
