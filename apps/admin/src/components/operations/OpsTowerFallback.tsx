"use client";

import { Radio } from "lucide-react";
import { PageSkeleton } from "@porterchain/ui/loading";
import AdminPage from "@/components/layout/AdminPage";
import OpsPageHero from "@/components/layout/OpsPageHero";

/** Suspense shell for Control Tower — chrome + empty map slot, not a centered spinner. */
export function OpsTowerFallback() {
  return (
    <AdminPage className="!space-y-3">
      <div className="ops-tower space-y-3">
        <OpsPageHero
          icon={Radio}
          title="Control Tower"
          description="Assign waiting work, clear exceptions, and watch the network live."
        />
        <div
          className="ops-table-scroll flex gap-1 rounded-2xl border border-primary/10 bg-white p-1.5"
          aria-hidden
        >
          {["Desk", "Board", "Orders", "Attention", "Tools"].map((label) => (
            <span key={label} className="rounded-xl px-3 py-2 text-sm font-medium text-primary/40">
              {label}
            </span>
          ))}
        </div>
        <div
          className="min-h-[22rem] rounded-2xl border border-primary/10 bg-primary/[0.03] p-4"
          role="status"
          aria-live="polite"
        >
          <p className="sr-only">Loading control tower</p>
          <PageSkeleton rows={2} />
        </div>
      </div>
    </AdminPage>
  );
}
