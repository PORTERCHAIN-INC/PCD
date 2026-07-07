import type { CustomerApi } from "@porterchain/mobile-api";
import { CUSTOMER_OFFLINE_ACTIONS } from "@porterchain/mobile-api";
import type { OfflineSyncAdapter } from "@porterchain/mobile-api";

export function createCustomerOfflineSyncAdapter(api: CustomerApi): OfflineSyncAdapter {
  return {
    queueAction: async (actionType, payload) => {
      if (
        actionType === CUSTOMER_OFFLINE_ACTIONS.SUPPORT_CREATE ||
        actionType === CUSTOMER_OFFLINE_ACTIONS.CLAIM_CREATE
      ) {
        return api.createSupport({
          subject: String(payload.subject ?? "Support"),
          description: payload.description ? String(payload.description) : undefined,
          order_id: payload.order_id ? String(payload.order_id) : undefined,
        });
      }
      throw new Error(`unsupported_customer_offline_action:${actionType}`);
    },
    sync: async () => ({ synced: 0, failed: 0 }),
    retryFailed: async () => ({ synced: 0, failed: 0, retried: 0 }),
    executeDirect: async (actionType, payload) => {
      if (
        actionType === CUSTOMER_OFFLINE_ACTIONS.SUPPORT_CREATE ||
        actionType === CUSTOMER_OFFLINE_ACTIONS.CLAIM_CREATE
      ) {
        return api.createSupport({
          subject: String(payload.subject ?? "Support"),
          description: payload.description ? String(payload.description) : undefined,
          order_id: payload.order_id ? String(payload.order_id) : undefined,
        });
      }
      throw new Error(`unsupported_customer_offline_action:${actionType}`);
    },
  };
}
