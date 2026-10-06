"use client";

import dynamic from "next/dynamic";
import MagicCard from "@/components/magic/MagicCard";
import ShimmerButton from "@/components/magic/ShimmerButton";
import WithGoogleMaps from "@/components/maps/WithGoogleMaps";
import RouteList from "@/components/routes/RouteList";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

type Tab = "plan" | "single" | "csv" | "recurring";

const BookDeliveryClient = dynamic(() => import("@/components/booking/BookDeliveryClient"), {
  loading: () => <PageSkeleton rows={5} />,
});
const BulkUploadClient = dynamic(() => import("@/components/bulk/BulkUploadClient"), {
  loading: () => <PageSkeleton rows={4} />,
});
const StandingOrdersClient = dynamic(() => import("@/components/routes/StandingOrdersClient"), {
  loading: () => <PageSkeleton rows={3} />,
});
const RouteModuleForm = dynamic(() => import("@/components/routes/RouteModuleForm"), {
  loading: () => <PageSkeleton rows={5} />,
});

function parseTab(value: string | null): Tab {
  if (value === "single" || value === "csv" || value === "plan" || value === "recurring")
    return value;
  return "plan";
}

export default function RoutesClient() {
  return (
    <Suspense fallback={<PageSkeleton rows={4} />}>
      <RoutesPageInner />
    </Suspense>
  );
}

function RoutesPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const tab = parseTab(searchParams.get("tab"));
  const [refreshKey, setRefreshKey] = useState(0);
  const [open, setOpen] = useState(false);
  const [plannerKey, setPlannerKey] = useState(0);

  useEffect(() => {
    if (tab === "plan" && searchParams.get("new") === "1") {
      setPlannerKey((value) => value + 1);
      setOpen(true);
    }
  }, [searchParams, tab]);

  function setTab(next: Tab) {
    const params = new URLSearchParams(searchParams.toString());
    if (next === "plan") params.delete("tab");
    else params.set("tab", next);
    params.delete("new");
    const query = params.toString();
    router.replace(query ? `/routes?${query}` : "/routes");
  }

  function openPlanner() {
    setPlannerKey((value) => value + 1);
    setOpen(true);
  }

  return (
    <div className="mx-auto w-full min-w-0 max-w-5xl space-y-6">
      <MagicCard className="min-w-0 p-4 sm:p-6" clip={false}>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-secondary">
              Operations
            </p>
            <h1 className="mt-1 text-xl font-semibold text-primary sm:text-2xl">Routes</h1>
            <p className="mt-1 max-w-xl text-sm text-muted">
              Book a single delivery, plan a multi-stop route, upload a CSV, or turn on a saved
              booking on a schedule. Shopify shops send orders through Integrations instead.
            </p>
          </div>
          {tab === "plan" ? (
            <ShimmerButton className="w-full shrink-0 sm:w-auto" onClick={openPlanner}>
              Add route
            </ShimmerButton>
          ) : null}
        </div>
        <div
          className="ops-tab-rail mt-5 w-full rounded-full border border-primary/10 bg-gray-bg/60 sm:w-fit"
          role="tablist"
        >
          {(
            [
              ["plan", "Multi-stop"],
              ["single", "Single"],
              ["csv", "CSV"],
              ["recurring", "Recurring"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={tab === id}
              onClick={() => setTab(id)}
              className={`min-h-10 shrink-0 rounded-full px-4 py-1.5 text-sm font-medium whitespace-nowrap ${
                tab === id ? "bg-primary text-white" : "text-primary hover:bg-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </MagicCard>

      {/* List-only plan tab: no Maps JS. Maps load for Single tab + planner dialog only. */}
      {tab === "plan" ? <RouteList refreshKey={refreshKey} /> : null}
      {tab === "single" ? (
        <WithGoogleMaps>
          <BookDeliveryClient embedded />
        </WithGoogleMaps>
      ) : null}
      {tab === "csv" ? (
        <WithGoogleMaps>
          <BulkUploadClient />
        </WithGoogleMaps>
      ) : null}
      {tab === "recurring" ? <StandingOrdersClient /> : null}

      {tab === "plan" && open ? (
        <RoutePlannerDialog
          plannerKey={plannerKey}
          onClose={() => setOpen(false)}
          onConfirmed={() => setRefreshKey((value) => value + 1)}
        />
      ) : null}
    </div>
  );
}

function RoutePlannerDialog({
  plannerKey,
  onClose,
  onConfirmed,
}: {
  plannerKey: number;
  onClose: () => void;
  onConfirmed: () => void;
}) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-6">
      <button
        type="button"
        aria-label="Close route planner"
        className="absolute inset-0 bg-primary/50 backdrop-blur-[2px]"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-route-title"
        className="relative flex max-h-[96dvh] w-full max-w-6xl flex-col overflow-hidden rounded-t-3xl border border-white/40 bg-gray-bg shadow-2xl sm:rounded-3xl"
      >
        <div className="flex items-center justify-between gap-3 border-b border-primary/10 bg-white px-4 py-3 sm:px-5 sm:py-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-secondary">
              Route planner
            </p>
            <h2 id="add-route-title" className="truncate text-lg font-semibold text-primary">
              Add route
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="min-h-10 shrink-0 rounded-full border border-primary/15 px-4 py-2 text-sm font-medium text-primary hover:bg-gray-bg"
          >
            Close
          </button>
        </div>
        <div className="min-h-0 overflow-y-auto px-4 py-5 sm:px-6">
          <WithGoogleMaps>
            <RouteModuleForm key={plannerKey} showTitle={false} onConfirmed={onConfirmed} />
          </WithGoogleMaps>
        </div>
      </div>
    </div>
  );
}
