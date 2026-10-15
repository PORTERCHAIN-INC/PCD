import { API_BASE } from "@/lib/api";

export type CustomerAttachment = {
  id: string;
  stop: "pickup" | "dropoff";
  kind_label: string;
  filename: string;
  required_at_stop: boolean;
  status: "waiting" | "viewed_by_driver" | "shown_at_pickup";
  purged: boolean;
};
export type CustomerAttachmentList = {
  items: CustomerAttachment[];
  editable: { pickup: boolean; dropoff: boolean };
};
export type PendingFile = { file: File; required: boolean };

export const ACCEPT = "application/pdf,image/png,image/jpeg,image/heic,image/heif,.heic,.heif";
export const STATUS_LABEL: Record<CustomerAttachment["status"], string> = {
  waiting: "Not opened yet",
  viewed_by_driver: "Viewed by driver",
  shown_at_pickup: "Shown at pickup",
};

const h = (token: string) => ({ Authorization: `Bearer ${token}`, "X-Porterchain-Portal": "customer" });

async function ok<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const b = (await r.json().catch(() => ({}))) as { detail?: unknown };
    const code = typeof b.detail === "string" ? b.detail : "";
    const copy: Record<string, string> = {
      attachment_type_not_allowed: "Use a PDF, JPG, PNG or HEIC file.",
      attachment_too_large: "That file is over 10 MB.",
      attachment_active_content: "That PDF contains scripts, so we can't accept it.",
      attachment_stop_closed: "This stop is already done.",
    };
    throw new Error(copy[code] ?? "Couldn't save that document. Try again.");
  }
  return (r.status === 204 ? undefined : r.json()) as Promise<T>;
}

/** `key` is the tracking number (or order id); the API scopes it to this customer. */
export const customerAttachments = {
  list: (token: string, key: string) =>
    fetch(`${API_BASE}/v1/customers/me/orders/${encodeURIComponent(key)}/attachments`, { headers: h(token) }).then((r) =>
      ok<CustomerAttachmentList>(r)
    ),
  upload: (token: string, key: string, file: File, required: boolean) => {
    const fd = new FormData();
    fd.set("file", file);
    fd.set("required_at_stop", String(required));
    return fetch(`${API_BASE}/v1/customers/me/orders/${encodeURIComponent(key)}/attachments`, {
      method: "POST",
      headers: h(token),
      body: fd,
    }).then((r) => ok<CustomerAttachment>(r));
  },
  remove: (token: string, id: string) =>
    fetch(`${API_BASE}/v1/customers/me/attachments/${id}`, { method: "DELETE", headers: h(token) }).then((r) => ok<void>(r)),
  open: async (token: string, id: string) => {
    const r = await fetch(`${API_BASE}/v1/customers/me/attachments/${id}/file`, { headers: h(token) });
    if (!r.ok) throw new Error("Couldn't open that document.");
    const url = URL.createObjectURL(await r.blob());
    window.open(url, "_blank", "noopener");
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  },
};

// Files picked before checkout survive the Stripe redirect in IndexedDB (this browser only).
const DB = "pc-booking-files";
function idb(): Promise<IDBDatabase> {
  return new Promise((res, rej) => {
    const r = indexedDB.open(DB, 1);
    r.onupgradeneeded = () => r.result.createObjectStore("pending");
    r.onsuccess = () => res(r.result);
    r.onerror = () => rej(r.error);
  });
}
export async function stashFiles(quoteId: string, files: PendingFile[]) {
  const db = await idb();
  await new Promise<void>((res, rej) => {
    const tx = db.transaction("pending", "readwrite");
    tx.objectStore("pending").put(files.map((f) => ({ blob: f.file, name: f.file.name, type: f.file.type, required: f.required })), quoteId);
    tx.oncomplete = () => res();
    tx.onerror = () => rej(tx.error);
  });
}
export async function takeStash(quoteId: string): Promise<PendingFile[]> {
  const db = await idb();
  return new Promise((res) => {
    const tx = db.transaction("pending", "readwrite");
    const store = tx.objectStore("pending");
    const g = store.get(quoteId);
    g.onsuccess = () => {
      const rows = (g.result ?? []) as Array<{ blob: Blob; name: string; type: string; required: boolean }>;
      store.delete(quoteId);
      res(rows.map((r) => ({ file: new File([r.blob], r.name, { type: r.type }), required: r.required })));
    };
    g.onerror = () => res([]);
  });
}
export async function attachAll(token: string, key: string, files: PendingFile[]): Promise<string[]> {
  const failed: string[] = [];
  for (const f of files) {
    try {
      await customerAttachments.upload(token, key, f.file, f.required);
    } catch {
      failed.push(f.file.name);
    }
  }
  return failed;
}
