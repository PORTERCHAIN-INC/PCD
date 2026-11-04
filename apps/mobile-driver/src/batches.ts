/**
 * Bulk batches for drivers (same logic as driver-portal/src/lib/batches.ts):
 * pickup (list + spot check + count/photo/handover + documents + must-read notes), scan advice,
 * grouped building delivery, driver-to-driver handover and leftovers. Gates come from @porterchain/driver-flows.
 */
import {
  blockersFor,
  type FlowContext,
  type FlowSpec,
  type ScanAdvice,
} from "@porterchain/driver-flows";

export type Fetcher = <T>(path: string, init?: { method?: string; body?: string }) => Promise<T>;

export type BatchParcel = {
  id: string;
  barcode: string;
  client_labels: string[];
  stop_seq: number | null;
  building_key: string;
  unit: string | null;
  address: string;
  recipient: string | null;
  handling: string[];
  scan_required: boolean;
  status: string;
  load_position?: number;
};
export type DocItem = {
  doc_type: string;
  label: string;
  blocking: boolean;
  needs_seal: boolean;
  status: "todo" | "captured" | "missing";
};
export type DocChecklist = { items: DocItem[]; blockers: string[]; reminders: string[] };
export type Instruction = {
  id: string;
  parcel_id: string | null;
  text: string;
  photo_key: string | null;
  priority: "normal" | "high" | "must_read";
  steps: string[];
  version: number;
  author_role: string;
  acknowledged?: boolean;
};
export type StepInstructions = { items: Instruction[]; must_ack: string[] };
export type PickupView = {
  route_id: string;
  status: string;
  expected: number;
  parcels: BatchParcel[];
  scan_required: string[];
  spot_sample: string[];
  carry_for: Record<string, string>;
  pickup_source: string;
  documents: DocChecklist;
  instructions: StepInstructions;
  flow_spec: {
    pickup: FlowSpec;
    delivery: FlowSpec;
    close: FlowSpec;
    handover_give: FlowSpec;
    handover_receive: FlowSpec;
  };
};
export type BatchStop = {
  building_key: string;
  address: string;
  stop_seq: number | null;
  parcels: BatchParcel[];
  handling: string[];
  eta_s?: number | null;
  flow_spec: FlowSpec;
};
export type RouteItem = {
  id: string;
  batch_id: string;
  route_no: number;
  wave: number;
  status: string;
};

const P = "/v1/batches";
const post = (body: unknown) => ({ method: "POST", body: JSON.stringify(body) });

export function batchClient(f: Fetcher) {
  return {
    routes: () => f<{ items: RouteItem[] }>(`${P}/routes`),
    summary: (id: string) => f<Record<string, unknown>>(`${P}/routes/${id}`),
    pickup: (id: string) => f<PickupView>(`${P}/routes/${id}/pickup`),
    confirmPickup: (id: string, body: Record<string, unknown>) =>
      f<{ status: string }>(`${P}/routes/${id}/pickup/confirm`, post(body)),
    failPickup: (id: string, reason: string) =>
      f(`${P}/routes/${id}/pickup/fail`, post({ reason })),
    scan: (id: string, code: string, phase: "pickup" | "delivery", scanned: string[]) =>
      f<ScanAdvice & { instructions?: Instruction[] }>(
        `${P}/routes/${id}/scan`,
        post({ code, phase, scanned })
      ),
    stops: (id: string) => f<{ stops: BatchStop[] }>(`${P}/routes/${id}/stops`),
    deliver: (id: string, codes: string[], extra: Record<string, unknown> = {}) =>
      f<{ delivered: string[] }>(`${P}/routes/${id}/deliver`, post({ codes, ...extra })),
    close: (id: string, dispositions: Record<string, string>) =>
      f(`${P}/routes/${id}/close`, post({ dispositions })),
    lookup: (id: string, q: string) =>
      f<{ items: BatchParcel[] }>(`${P}/routes/${id}/lookup?q=${encodeURIComponent(q)}`),
    linkLabel: (id: string, parcel_id: string, code: string) =>
      f(`${P}/routes/${id}/link-label`, post({ parcel_id, code })),
    handover: (
      id: string,
      body: {
        to_driver_id: string;
        codes: string[];
        photo_key: string;
        lat: number;
        lng: number;
        place_kind: string;
      }
    ) => f<{ handover_id: string }>(`${P}/routes/${id}/handovers`, post(body)),
    incoming: () =>
      f<{ items: { id: string; from_driver_id: string; parcels: number; place_kind: string }[] }>(
        `${P}/handovers/incoming`
      ),
    accept: (hid: string, body: Record<string, unknown>) =>
      f(`${P}/handovers/${hid}/accept`, post(body)),
    docs: (id: string, phase: "before_arrival" | "at_pickup" = "at_pickup") =>
      f<DocChecklist>(`/v1/doc-checklist/routes/${id}?phase=${phase}`),
    captureDoc: (
      id: string,
      doc: string,
      body: {
        media_key?: string;
        scan_code?: string;
        seal_no?: string;
        shipper_name: string;
        shipper_signature_key: string;
      }
    ) => f<DocChecklist>(`/v1/doc-checklist/routes/${id}/${doc}`, post(body)),
    docMissing: (id: string, doc: string, reason: string) =>
      f<DocChecklist>(`/v1/doc-checklist/routes/${id}/${doc}/missing`, post({ reason })),
    instructions: (id: string, step: "pickup" | "scan" | "delivery", parcelId?: string) =>
      f<StepInstructions>(
        `/v1/instructions/routes/${id}?step=${step}${parcelId ? `&parcel_id=${parcelId}` : ""}`
      ),
    ack: (iid: string) => f<{ ok: boolean }>(`/v1/instructions/${iid}/ack`, post({})),
  };
}

export type PickupState = {
  scanned: string[];
  counted?: number;
  photo?: boolean;
  merchantConfirmed?: boolean;
  countException?: boolean;
  acked: string[];
};

/** FlowContext for the pickup gate, from the server view + what the driver has done locally. */
export function pickupContext(v: PickupView, s: PickupState): FlowContext {
  const docs: Record<string, "captured" | "missing" | "todo"> = {};
  for (const d of v.documents.items) docs[d.doc_type] = d.status;
  return {
    atStop: true,
    scanned: s.scanned,
    spotSample: v.spot_sample,
    scanRequired: v.scan_required,
    counted: s.counted,
    expectedCount: v.expected,
    photo: s.photo,
    merchantConfirmed: s.merchantConfirmed,
    countException: s.countException,
    docsRequired: v.documents.items.map((d) => d.doc_type),
    docsNonBlocking: v.documents.items.filter((d) => !d.blocking).map((d) => d.doc_type),
    docs,
    mustAck: v.instructions.must_ack,
    acked: s.acked,
  };
}

/** Every blocker across the pickup spec, in order, so the screen shows what's left. */
export function pickupBlockers(v: PickupView, s: PickupState): string[] {
  const ctx = pickupContext(v, s);
  return v.flow_spec.pickup.steps.flatMap((st) =>
    blockersFor(st.block_if, ctx, v.flow_spec.pickup)
  );
}

/** Leftovers at close = parcels still on the van. */
export function leftovers(stops: BatchStop[]): string[] {
  return stops.flatMap((s) =>
    s.parcels.filter((p) => p.status !== "delivered").map((p) => p.barcode)
  );
}

export function buildingBlockers(stop: BatchStop, scanned: string[]): string[] {
  const open = stop.parcels.filter((p) => p.status !== "delivered").map((p) => p.barcode);
  return blockersFor(
    ["building_scan_incomplete"],
    { buildingExpected: open, scanned },
    stop.flow_spec
  );
}
