import type { Metadata } from "next";
import DashboardClient from "@/components/dashboard/DashboardClient";
import { TodayOps } from "@/components/today/TodayOps";

export const metadata: Metadata = { title: "Today" };

/** Doc 75: one home. The old /dashboard KPIs live here under "Network KPIs". */
export default function TodayPage() {
  return (
    <>
      <TodayOps />
      <details className="mt-8 rounded-xl border p-4">
        <summary className="cursor-pointer text-sm font-semibold">Network KPIs and alerts</summary>
        <div className="mt-4">
          <DashboardClient />
        </div>
      </details>
    </>
  );
}
