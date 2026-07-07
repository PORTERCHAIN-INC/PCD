import type { ApiClient } from "./client";

export type SecurityAuditEventPayload = {
  event_type: string;
  app_kind: "customer" | "driver";
  occurred_at?: string;
  metadata?: Record<string, unknown>;
};

export function createSecurityApi(client: ApiClient, v1 = "/v1") {
  return {
    postAuditEvents: (events: SecurityAuditEventPayload[]) =>
      client.post<{ accepted: number }>(`${v1}/security/audit-events`, { events }),
  };
}
