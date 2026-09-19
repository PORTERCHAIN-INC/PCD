import type { EventActor, EventEnvelope } from "@porterchain/types";

export function createEventEnvelope<T extends Record<string, unknown>>(params: {
  eventType: string;
  aggregateType: string;
  aggregateId: string;
  payload?: T;
  correlationId?: string;
  actor?: EventActor;
}): EventEnvelope<T> {
  return {
    eventId: crypto.randomUUID(),
    eventType: params.eventType,
    occurredAt: new Date().toISOString(),
    aggregateType: params.aggregateType,
    aggregateId: params.aggregateId,
    correlationId: params.correlationId,
    actor: params.actor ?? { type: "system" },
    payload: (params.payload ?? {}) as T,
    version: 1,
  };
}
