import { publicEnv } from "@/lib/env";

const API_BASE = publicEnv.porterchainApiUrl;

export type BookingAttachment = {
  id: string;
  order_id: string | null;
  stop: "pickup" | "dropoff";
  kind: string;
  kind_label: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  note: string | null;
  required_at_stop: boolean;
  from_location_template: boolean;
  status: "waiting" | "viewed_by_driver" | "shown_at_pickup";
  viewed_at: string | null;
  shown_at: string | null;
  has_proof_photo: boolean;
  purged: boolean;
};

export type AttachmentList = {
  items: BookingAttachment[];
  kinds: Record<string, string>;
  max_bytes: number;
  editable: { pickup: boolean; dropoff: boolean };
};

export const ACCEPT = "application/pdf,image/png,image/jpeg,image/heic,image/heif,.heic,.heif";

function headers(token: string, orgId?: string): Record<string, string> {
  const h: Record<string, string> = { Authorization: `Bearer ${token}`, "X-Porterchain-Portal": "merchant" };
  if (orgId) h["X-Merchant-Id"] = orgId;
  return h;
}

async function ok<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    const d = (body as { detail?: unknown }).detail;
    throw new Error(attachmentErrorCopy(typeof d === "string" ? d : `error_${r.status}`));
  }
  return (r.status === 204 ? undefined : r.json()) as Promise<T>;
}

export function attachmentErrorCopy(code: string): string {
  const copy: Record<string, string> = {
    attachment_type_not_allowed: "Use a PDF, JPG, PNG or HEIC file.",
    attachment_too_large: "That file is over 10 MB. Try a smaller scan or photo.",
    attachment_empty: "That file is empty.",
    attachment_active_content: "That PDF contains scripts, so we can't accept it. Print it to PDF again and retry.",
    attachment_malware_detected: "That file failed the security scan.",
    attachment_stop_closed: "This stop is already done, so its documents can't change.",
    attachment_limit_reached: "A booking can hold up to 10 documents.",
  };
  return copy[code] ?? "Something went wrong with that document. Try again.";
}

export const attachmentsApi = {
  list: (token: string, orderId: string, orgId?: string) =>
    fetch(`${API_BASE}/v1/merchant/orders/${orderId}/attachments`, { headers: headers(token, orgId) }).then(
      (r) => ok<AttachmentList>(r)
    ),
  suggest: (token: string, file: File, orgId?: string) => {
    const fd = new FormData();
    fd.set("file", file);
    return fetch(`${API_BASE}/v1/merchant/attachments/suggest`, {
      method: "POST",
      headers: headers(token, orgId),
      body: fd,
    }).then((r) => ok<{ kind: string; kind_label: string; stop: "pickup" | "dropoff" }>(r));
  },
  upload: (
    token: string,
    orderId: string,
    file: File,
    opts: { kind: string; stop: string; required: boolean; note?: string; saveForLocation: boolean },
    orgId?: string
  ) => {
    const fd = new FormData();
    fd.set("file", file);
    fd.set("kind", opts.kind);
    fd.set("stop", opts.stop);
    fd.set("required_at_stop", String(opts.required));
    fd.set("save_for_location", String(opts.saveForLocation));
    if (opts.note) fd.set("note", opts.note);
    return fetch(`${API_BASE}/v1/merchant/orders/${orderId}/attachments`, {
      method: "POST",
      headers: headers(token, orgId),
      body: fd,
    }).then((r) => ok<BookingAttachment>(r));
  },
  remove: (token: string, id: string, orgId?: string) =>
    fetch(`${API_BASE}/v1/merchant/attachments/${id}`, { method: "DELETE", headers: headers(token, orgId) }).then(
      (r) => ok<void>(r)
    ),
  open: async (token: string, id: string, orgId?: string) => {
    const r = await fetch(`${API_BASE}/v1/merchant/attachments/${id}/file`, { headers: headers(token, orgId) });
    if (!r.ok) throw new Error(attachmentErrorCopy("open_failed"));
    const url = URL.createObjectURL(await r.blob());
    window.open(url, "_blank", "noopener");
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  },
};
