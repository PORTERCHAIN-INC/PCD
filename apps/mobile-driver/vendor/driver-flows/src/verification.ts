/** Pickup verification by risk — mirrors apps/api batch_engine/scenarios.verification_blockers.
 * Low risk: count + photo + merchant confirm + server-chosen 3-5 spot scans.
 * High risk (pharmacy, high_value, contract, customs): every such parcel scanned. */
export const HIGH_RISK = ["pharmacy", "high_value", "contract", "customs"] as const;

export interface VerifyParcel {
  barcode: string;
  handling?: string[];
  scan_required?: boolean;
}
export interface VerifyState {
  counted: number | null;
  photo: boolean;
  merchantConfirmed: boolean;
  scanned: string[];
}

export function isHighRisk(p: VerifyParcel): boolean {
  return (
    !!p.scan_required ||
    (p.handling ?? []).some((h) => (HIGH_RISK as readonly string[]).includes(h))
  );
}

export function riskLevel(parcels: VerifyParcel[]): "low" | "high" | "mixed" {
  const high = parcels.filter(isHighRisk).length;
  return high === 0 ? "low" : high === parcels.length ? "high" : "mixed";
}

export function mustScan(parcels: VerifyParcel[], spot: string[]): string[] {
  return [...new Set([...parcels.filter(isHighRisk).map((p) => p.barcode), ...spot])].sort();
}

export function verificationBlockers(
  parcels: VerifyParcel[],
  spot: string[],
  s: VerifyState
): string[] {
  const out: string[] = [];
  if (s.counted === null) out.push("count_required");
  if (!s.photo) out.push("photo_required");
  if (!s.merchantConfirmed) out.push("merchant_confirm_required");
  const seen = new Set(s.scanned);
  for (const b of mustScan(parcels, spot)) if (!seen.has(b)) out.push(`scan_required:${b}`);
  return out;
}
