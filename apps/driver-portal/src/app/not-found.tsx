import Link from "next/link";

export default function DriverNotFound() {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white px-6 py-10">
      <h1 className="text-lg font-semibold text-primary">That job is not here</h1>
      <Link href="/jobs" className="mt-4 inline-flex text-sm font-semibold text-secondary">
        Back to jobs
      </Link>
    </div>
  );
}
