"use client";

export function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-primary/10 p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-xl font-bold text-primary">{value}</p>
      {sub && <p className="text-xs text-muted">{sub}</p>}
    </div>
  );
}

export function Detail({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium text-primary">{value || "—"}</dd>
    </div>
  );
}
