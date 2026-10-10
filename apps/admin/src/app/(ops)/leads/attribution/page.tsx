import Link from "next/link";
import LeadAttributionView, {
  type LeadAttributionSummary,
} from "@/components/leads/LeadAttributionView";
import { adminServerFetch } from "@/lib/server-api";

export default async function LeadAttributionPage({
  searchParams,
}: {
  searchParams: Promise<{ days?: string }>;
}) {
  const { days: raw } = await searchParams;
  const days = Math.min(365, Math.max(1, Number.parseInt(raw ?? "30", 10) || 30));
  const data = await adminServerFetch<LeadAttributionSummary>(
    `/v1/admin/marketing/lead-attribution?days=${days}`
  );
  return (
    <div className="space-y-6 p-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-secondary">Sales</p>
          <h1 className="text-3xl font-extrabold tracking-tight text-primary">Attribution</h1>
          <p className="text-sm text-slate-600">
            Where leads come from: source, industry, postal area (FSA) and UTM campaign.
          </p>
        </div>
        <nav className="flex gap-2 text-sm">
          {[7, 30, 90].map((d) => (
            <Link
              key={d}
              href={`/leads/attribution?days=${d}`}
              className={`rounded-lg border px-3 py-1.5 ${
                d === days ? "border-blue-500 bg-blue-50 text-blue-700" : "border-slate-200"
              }`}
            >
              {d} days
            </Link>
          ))}
        </nav>
      </header>
      <LeadAttributionView data={data} />
    </div>
  );
}
