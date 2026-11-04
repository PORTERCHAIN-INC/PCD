import type { FlowContext, FlowSpec } from "./types";

type Check = (c: FlowContext, spec: FlowSpec) => boolean;

const sameSet = (a: string[] = [], b: string[] = []) =>
  a.length === b.length && [...a].sort().join("|") === [...b].sort().join("|");

/** Each returns true when the step is BLOCKED. Run locally on cached values; the server re-verifies on sync. */
export const BLOCK_CHECKS: Record<string, Check> = {
  not_at_stop: (c) => c.atStop === false,
  not_at_pickup: (c) => c.atStop === false,
  offer_expired: (c) => !!c.offerExpired,
  dvir_missing: (c) => !c.dvirDone,
  hos_block: (c) => !!c.hosBlocked,
  count_mismatch: (c) => !!c.expectedScans && !sameSet(c.scanned, c.expectedScans),
  scan_mismatch: (c) =>
    !!c.expectedScans && (c.scanned ?? []).some((s) => !c.expectedScans!.includes(s)),
  unknown_package: (c) =>
    !!c.expectedScans && (c.scanned ?? []).some((s) => !c.expectedScans!.includes(s)),
  wrong_zone: (c) => c.zoneOk === false,
  seal_mismatch: (c) => !c.sealNo || (!!c.expectedSealNo && c.sealNo !== c.expectedSealNo),
  temp_out_of_range: (c, s) => {
    const [lo, hi] = s.temp_range_c ?? [2, 8];
    return c.tempC == null || c.tempC < lo || c.tempC > hi;
  },
  id_fail: (c) => c.idNameMatch !== true,
  under_19: (c) => c.recipientAge == null || c.recipientAge < 19,
  agent_not_named: (c) => c.idNameMatch !== true && !c.agentNamed,
  no_signature: (c) => !c.signature,
  dolly_missing: (c) => !c.dollyConfirmed,
  over_dolly_safe_limit: (c) => Boolean(c.overDollyLimit),
  no_before_photos: (c) => !c.beforePhotos,
  bol_missing: (c) => !c.bolPresent,
  count_short_without_osd: (c) =>
    c.unitsExpected != null && (c.unitsCounted ?? 0) < c.unitsExpected && !c.osdNote?.trim(),
  no_reason: (c) => !c.reason,
  same_day_return_required: () => false, // enforced server-side: a return task is forced
  // Bulk batches (pickup = count + one photo + handover; spot sample; per-parcel only where required)
  spot_check_incomplete: (c) => (c.spotSample ?? []).some((b) => !(c.scanned ?? []).includes(b)),
  per_parcel_scan_required: (c) =>
    (c.scanRequired ?? []).some((b) => !(c.scanned ?? []).includes(b)),
  count_not_entered: (c) => c.counted == null || c.counted < 0,
  photo_missing: (c) => !c.photo,
  count_mismatch_unreported: (c) =>
    c.counted != null &&
    c.expectedCount != null &&
    c.counted !== c.expectedCount &&
    !c.countException,
  merchant_not_confirmed: (c) => !c.merchantConfirmed,
  pickup_not_confirmed: (c) => !c.pickupConfirmed,
  building_scan_incomplete: (c) =>
    (c.buildingExpected ?? []).some((b) => !(c.scanned ?? []).includes(b)),
  handover_needs_photo_and_location: (c) => !c.photo || !c.location,
  handover_scan_mismatch: (c) =>
    !!c.handoverExpected &&
    !sameSet(c.scanned, c.handoverExpected) &&
    c.counted !== c.handoverExpected.length,
  leftover_without_disposition: (c) => (c.leftovers ?? []).some((b) => !c.dispositions?.[b]),
  pickup_docs_missing: (c) =>
    (c.docsRequired ?? []).some((d) => {
      const st = c.docs?.[d];
      return !(st === "captured" || (st === "missing" && (c.docsNonBlocking ?? []).includes(d)));
    }),
  instruction_not_acknowledged: (c) =>
    (c.mustAck ?? []).some((id) => !(c.acked ?? []).includes(id)),
};

export function blockersFor(blockIf: string[], ctx: FlowContext, spec: FlowSpec): string[] {
  // Unknown check ids block (fail closed) so a newer server spec never silently skips a rule.
  return blockIf.filter((id) => (BLOCK_CHECKS[id] ? BLOCK_CHECKS[id](ctx, spec) : true));
}
