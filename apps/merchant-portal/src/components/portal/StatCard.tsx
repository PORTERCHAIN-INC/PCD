export function StatCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="min-w-0 rounded-2xl border border-primary/10 bg-white p-4 sm:p-5">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-2 truncate text-2xl font-bold tabular-nums text-primary">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}
