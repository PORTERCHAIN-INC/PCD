import type { MobileAppKind, SecurityAuditEvent, SecurityAuditEventType } from "../types";
import {
  getJsonEncrypted,
  getEncryptedMmkvStore,
  setJsonEncrypted,
} from "../storage/encrypted-mmkv";

const BUFFER_KEY = "security.audit_buffer";
const MAX_BUFFER = 100;

let appKindRef: MobileAppKind = "customer";
let flushHandler: ((events: SecurityAuditEvent[]) => Promise<void>) | null = null;

export function configureAuditBuffer(
  appKind: MobileAppKind,
  flush?: (events: SecurityAuditEvent[]) => Promise<void>
) {
  appKindRef = appKind;
  flushHandler = flush ?? null;
}

export async function emitSecurityEvent(
  eventType: SecurityAuditEventType,
  metadata?: Record<string, unknown>
) {
  const event: SecurityAuditEvent = {
    event_type: eventType,
    app_kind: appKindRef,
    occurred_at: new Date().toISOString(),
    metadata,
  };

  const store = await getEncryptedMmkvStore("porterchain-security-audit");
  const buffer = getJsonEncrypted<SecurityAuditEvent[]>(store, BUFFER_KEY, []);
  buffer.push(event);
  if (buffer.length > MAX_BUFFER) buffer.splice(0, buffer.length - MAX_BUFFER);
  setJsonEncrypted(store, BUFFER_KEY, buffer);

  if (flushHandler && buffer.length >= 10) {
    await flushAuditBuffer();
  }
}

export async function flushAuditBuffer() {
  if (!flushHandler) return 0;
  const store = await getEncryptedMmkvStore("porterchain-security-audit");
  const buffer = getJsonEncrypted<SecurityAuditEvent[]>(store, BUFFER_KEY, []);
  if (buffer.length === 0) return 0;
  await flushHandler(buffer);
  setJsonEncrypted(store, BUFFER_KEY, []);
  return buffer.length;
}

export async function getBufferedAuditEvents() {
  const store = await getEncryptedMmkvStore("porterchain-security-audit");
  return getJsonEncrypted<SecurityAuditEvent[]>(store, BUFFER_KEY, []);
}
