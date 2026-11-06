/** Matches geo_resolve Candidate.to_dict() (API #183); structurally same as @porterchain/maps AddressCandidate. */
export interface AddressCandidate {
  formatted: string;
  lat: number;
  lng: number;
  city?: string | null;
  postal?: string | null;
  fsa?: string | null;
  score?: number;
  source?: string;
  place_id?: string | null;
}

/** Thin view of a route-import stop (API #183: geo_resolve candidates). */
export type RouteImportStopView = Record<string, unknown> & {
  geocode_status?: string;
  issues?: string[];
  candidates?: AddressCandidate[];
  raw_address?: string;
  address?: string;
  formatted?: string;
};

/** Indexes of stops the resolver flagged ambiguous (needs_review / address.ambiguous). */
export function routeImportReviewIndexes(
  job: { stops?: Array<Record<string, unknown>> } | null | undefined
): number[] {
  const out: number[] = [];
  (job?.stops ?? []).forEach((raw, i) => {
    const s = raw as RouteImportStopView;
    const issues = Array.isArray(s.issues) ? s.issues.map(String) : [];
    if (s.geocode_status === "needs_review" || issues.includes("address.ambiguous")) out.push(i);
  });
  return out;
}
