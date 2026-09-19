import type { QueueName } from "@porterchain/types";

export const Queues = {
  EMAILS: "emails",
  SMS: "sms",
  PUSH: "push",
  DISPATCH: "dispatch",
  ROUTING: "routing",
  BILLING: "billing",
  REPORTS: "reports",
  WEBHOOKS: "webhooks",
} as const satisfies Record<string, QueueName>;

export interface QueueMessage<T = Record<string, unknown>> {
  messageId: string;
  queue: QueueName;
  payload: T;
  enqueuedAt: string;
  retryCount: number;
}

export function queueRedisKey(queue: QueueName): string {
  return `porterchain:queue:${queue}`;
}
