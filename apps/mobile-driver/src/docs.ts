/** Driver documents: what's required, expiry warnings, and the one-line status for each. */
import type { DriverDocument } from "./api";

export const REQUIRED_DOCS = new Set(["license", "insurance", "vehicle_registration"]);
export const WARN_DAYS = 30;

export type DocHealth = "ok" | "expiring" | "expired" | "missing" | "review" | "rejected";

export function daysUntil(iso: string | null, now: number): number | null {
  if (!iso) return null;
  const t = Date.parse(iso.length === 10 ? `${iso}T23:59:59` : iso);
  if (Number.isNaN(t)) return null;
  return Math.floor((t - now) / 86_400_000);
}

export function docHealth(d: DriverDocument, now: number): DocHealth {
  const s = (d.status || "").toLowerCase();
  if (s === "rejected") return "rejected";
  if (s === "expired") return "expired";
  const left = daysUntil(d.expires_at, now);
  if (left != null && left < 0) return "expired";
  if (s === "missing" || (!d.has_file && !d.url && !d.verified)) return "missing";
  if (left != null && left <= WARN_DAYS) return "expiring";
  if (s === "pending_review") return "review";
  return "ok";
}

export function docLine(d: DriverDocument, now: number): string {
  const h = docHealth(d, now);
  const left = daysUntil(d.expires_at, now);
  switch (h) {
    case "missing":
      return REQUIRED_DOCS.has(d.type) ? "Required · not uploaded" : "Not uploaded";
    case "rejected":
      return d.rejection_reason ? `Rejected · ${d.rejection_reason}` : "Rejected · upload again";
    case "expired":
      return "Expired · replace now";
    case "expiring":
      return left === 0 ? "Expires today" : `Expires in ${left} day${left === 1 ? "" : "s"}`;
    case "review":
      return "In review";
    default:
      return d.expires_at ? `Valid · expires ${d.expires_at.slice(0, 10)}` : "Valid";
  }
}

/** Most urgent first: expired/rejected/missing-required, then expiring, review, ok. */
export function sortDocs(docs: DriverDocument[], now: number): DriverDocument[] {
  const rank: Record<DocHealth, number> = {
    expired: 0,
    rejected: 1,
    missing: 2,
    expiring: 3,
    review: 4,
    ok: 5,
  };
  return [...docs].sort((a, b) => {
    const ra = rank[docHealth(a, now)] - (REQUIRED_DOCS.has(a.type) ? 0.5 : 0);
    const rb = rank[docHealth(b, now)] - (REQUIRED_DOCS.has(b.type) ? 0.5 : 0);
    return ra - rb;
  });
}

/** Banner count for Me / Today: anything that blocks work or will soon. */
export function docAlerts(docs: DriverDocument[] | undefined, now: number): number {
  return (docs ?? []).filter((d) => {
    const h = docHealth(d, now);
    return (
      h === "expired" ||
      h === "rejected" ||
      h === "expiring" ||
      (h === "missing" && REQUIRED_DOCS.has(d.type))
    );
  }).length;
}

/** Optimistic: what the list shows the moment an upload is sent. */
export function optimisticUpload(
  docs: DriverDocument[],
  type: string,
  expires_at: string | null
): DriverDocument[] {
  return docs.map((d) =>
    d.type === type
      ? {
          ...d,
          status: "pending_review",
          verified: false,
          has_file: true,
          uploaded_at: new Date().toISOString(),
          expires_at: expires_at ?? d.expires_at,
          rejection_reason: null,
        }
      : d
  );
}
