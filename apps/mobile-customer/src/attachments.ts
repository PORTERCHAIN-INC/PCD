/**
 * Pickup / drop-off documents attached at booking (same API as porterchain.com):
 * the assigned driver sees them in the driver app and shows required ones at pickup.
 */
import * as DocumentPicker from "expo-document-picker";

import { apiBaseUrl } from "./config";
import { requireBearer } from "./session";

export type PendingDoc = {
  uri: string;
  name: string;
  mimeType: string;
  size: number;
  required: boolean;
};

export const MAX_DOCS = 5;
export const MAX_BYTES = 10 * 1024 * 1024;
const TYPES = ["application/pdf", "image/jpeg", "image/png", "image/heic", "image/heif"];

const COPY: Record<string, string> = {
  attachment_type_not_allowed: "Use a PDF, JPG, PNG or HEIC file.",
  attachment_too_large: "That file is over 10 MB.",
  attachment_active_content: "That PDF contains scripts, so we can't accept it.",
  attachment_stop_closed: "This stop is already done.",
};

export function attachmentError(code: string): string {
  return COPY[code] ?? "Couldn't save that document. Try again.";
}

/** Pick files; rejects wrong types / oversize locally with a clear reason. */
export async function pickDocuments(
  current: PendingDoc[]
): Promise<{ docs: PendingDoc[]; error: string | null }> {
  const res = await DocumentPicker.getDocumentAsync({
    type: TYPES,
    multiple: true,
    copyToCacheDirectory: true,
  });
  if (res.canceled) return { docs: current, error: null };
  let error: string | null = null;
  const next = [...current];
  for (const a of res.assets) {
    const mime = (a.mimeType ?? "").toLowerCase();
    if (mime && !TYPES.includes(mime)) {
      error = COPY.attachment_type_not_allowed;
      continue;
    }
    if ((a.size ?? 0) > MAX_BYTES) {
      error = COPY.attachment_too_large;
      continue;
    }
    if (next.length >= MAX_DOCS) {
      error = `Up to ${MAX_DOCS} documents per booking.`;
      break;
    }
    next.push({
      uri: a.uri,
      name: a.name,
      mimeType: mime || "application/pdf",
      size: a.size ?? 0,
      required: true,
    });
  }
  return { docs: next, error };
}

/** Upload one document to a booking (key = tracking number or order id). */
export async function uploadDocument(key: string, doc: PendingDoc): Promise<void> {
  const fd = new FormData();
  // React Native FormData file part.
  fd.append("file", { uri: doc.uri, name: doc.name, type: doc.mimeType } as unknown as Blob);
  fd.append("stop", "pickup");
  fd.append("required_at_stop", String(doc.required));
  const res = await fetch(
    `${apiBaseUrl}/v1/customers/me/orders/${encodeURIComponent(key)}/attachments`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${await requireBearer()}`,
        "X-Porterchain-Portal": "customer",
        Accept: "application/json",
      },
      body: fd,
    }
  );
  if (!res.ok) {
    let code = "";
    try {
      const b = (await res.json()) as { detail?: unknown };
      code = typeof b.detail === "string" ? b.detail : "";
    } catch {
      /* ignore */
    }
    throw new Error(attachmentError(code));
  }
}

/** Upload all; returns names that failed so the user can retry from the portal. */
export async function uploadAll(key: string, docs: PendingDoc[]): Promise<string[]> {
  const failed: string[] = [];
  for (const d of docs) {
    try {
      await uploadDocument(key, d);
    } catch {
      failed.push(d.name);
    }
  }
  return failed;
}
