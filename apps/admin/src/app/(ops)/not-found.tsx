import Link from "next/link";

export default function OpsNotFound() {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white px-6 py-10">
      <h1 className="text-lg font-semibold text-primary">That record is not here</h1>
      <p className="mt-1 text-sm text-muted">The link may be old, or the record was removed.</p>
      <Link href="/dashboard" className="mt-4 inline-flex text-sm font-semibold text-secondary">
        Back to dashboard
      </Link>
    </div>
  );
}
