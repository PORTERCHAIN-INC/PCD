export type Capture =
  | "scan"
  | "photo"
  | "seal_no"
  | "temp"
  | "id_name_match"
  | "signature"
  | "bol_signature"
  | "driver_ids"
  | "reason"
  | "dvir";

export type FlowStep = {
  id: string;
  card: string;
  capture: Capture[] | string[];
  block_if: string[];
  only_if?: string;
};

export type FlowSpec = {
  flow_id: string;
  version: number;
  locale_keys?: boolean;
  steps: FlowStep[];
  warn_if?: string[];
  multi_stop?: boolean;
  temp_range_c?: [number, number] | null;
};

export type JobFlowSpecs = { documents: string[]; pickup: FlowSpec; delivery: FlowSpec };

/** What the driver has captured so far plus facts the device knows (geofence, expected values). */
export type FlowContext = {
  atStop?: boolean;
  scanned?: string[];
  expectedScans?: string[];
  sealNo?: string;
  expectedSealNo?: string;
  tempC?: number;
  idNameMatch?: boolean;
  recipientAge?: number;
  agentNamed?: boolean;
  signature?: boolean;
  photos?: number;
  beforePhotos?: number;
  dollyConfirmed?: boolean;
  /** Heaviest parcel at this stop is over the one-driver dolly safe limit. */
  overDollyLimit?: boolean;
  bolPresent?: boolean;
  unitsCounted?: number;
  unitsExpected?: number;
  osdNote?: string;
  reason?: string;
  dvirDone?: boolean;
  hosBlocked?: boolean;
  offerExpired?: boolean;
  zoneOk?: boolean;
  flags?: Record<string, boolean>;
  // bulk batches
  counted?: number;
  expectedCount?: number;
  photo?: boolean;
  merchantConfirmed?: boolean;
  spotSample?: string[];
  scanRequired?: string[];
  countException?: boolean;
  pickupConfirmed?: boolean;
  buildingExpected?: string[];
  handoverExpected?: string[];
  location?: { lat: number; lng: number } | null;
  leftovers?: string[];
  dispositions?: Record<string, "return" | "reattempt">;
  // pickup documents + instructions
  docsRequired?: string[];
  docsNonBlocking?: string[];
  docs?: Record<string, "captured" | "missing" | "todo">;
  mustAck?: string[];
  acked?: string[];
};
