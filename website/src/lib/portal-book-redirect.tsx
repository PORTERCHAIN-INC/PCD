"use client";

import { Suspense, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { publicEnv } from "@/lib/env";

function PortalBookRedirectInner({ subpath }: { subpath: string }) {
  const searchParams = useSearchParams();

  useEffect(() => {
    const qs = searchParams.toString();
    const base = `${publicEnv.customerPortalUrl.replace(/\/$/, "")}/${subpath.replace(/^\//, "")}`;
    window.location.replace(qs ? `${base}?${qs}` : base);
  }, [searchParams, subpath]);

  return (
    <main className="min-h-[40vh] flex items-center justify-center px-6 text-center text-muted">
      Redirecting to the customer portal…
    </main>
  );
}

/** Website retail funnel → customer portal (:3004) per §1.1.4 · §1.4.1. */
export default function PortalBookRedirect({ subpath = "book" }: { subpath?: string }) {
  return (
    <Suspense
      fallback={
        <main className="min-h-[40vh] flex items-center justify-center px-6 text-center text-muted">
          Redirecting…
        </main>
      }
    >
      <PortalBookRedirectInner subpath={subpath} />
    </Suspense>
  );
}
