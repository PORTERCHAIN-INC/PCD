/** Pickup documents + job instructions client (admin: /v1/admin/jobs, merchant: /v1/merchant/jobs). */
export type Fetcher = <T>(path: string, init?: RequestInit) => Promise<T>;
export type JobKind = "orders" | "batches";
export type PickupDoc = {
  id: string;
  doc_type: string;
  status: string;
  media_key?: string | null;
  scan_code?: string | null;
  seal_no?: string | null;
  shipper_name?: string | null;
  captured_at?: string | null;
  note?: string | null;
  route_id?: string;
};
export type Instruction = {
  id: string;
  text: string;
  priority: string;
  visibility?: string[];
  steps?: string[];
  business?: boolean;
  author_role?: string;
  version: number;
  parcel_id?: string | null;
  photo_key?: string | null;
};
export type InstructionInput = {
  text: string;
  priority?: string;
  visibility?: string[];
  steps?: string[];
  business?: boolean;
  parcel_id?: string;
  photo_key?: string;
  as_partner_id?: string;
};
export type EditEntry = { action: string; author_role: string; author_id: string; at: string };

export const PRIORITIES = ["normal", "high", "must_read"] as const;
export const VISIBILITY = ["driver", "admin", "merchant", "customer", "partner"] as const;
export const STEPS = ["pickup", "scan", "delivery"] as const;

export function jobDocsClient(f: Fetcher, base: string) {
  const j = (body: unknown, method = "POST"): RequestInit => ({
    method,
    body: JSON.stringify(body),
  });
  return {
    docs: (k: JobKind, id: string) =>
      f<{ documents: PickupDoc[] }>(`${base}/${k}/${id}/pickup-docs`),
    list: (k: JobKind, id: string) =>
      f<{ items: Instruction[] }>(`${base}/${k}/${id}/instructions`),
    add: (k: JobKind, id: string, b: InstructionInput) =>
      f<{ id: string; version: number }>(`${base}/${k}/${id}/instructions`, j(b)),
    edit: (iid: string, b: Partial<InstructionInput> & { delete?: boolean }) =>
      f<{ id: string; version: number }>(`${base}/instructions/${iid}`, j(b, "PATCH")),
    history: (iid: string) => f<{ items: EditEntry[] }>(`${base}/instructions/${iid}/history`),
  };
}

/** Business notes are never driver-visible; must_read implies the driver sees it. */
export function normaliseInstruction(b: InstructionInput): InstructionInput {
  const vis = new Set(b.visibility ?? ["driver", "admin", "merchant"]);
  if (b.business) vis.delete("driver");
  else if (b.priority === "must_read") vis.add("driver");
  return {
    ...b,
    text: b.text.trim(),
    visibility: [...vis],
    steps: b.steps?.length ? b.steps : ["pickup", "delivery"],
  };
}

export function missingDocs(docs: PickupDoc[]): string[] {
  return docs.filter((d) => d.status === "missing").map((d) => d.doc_type);
}
