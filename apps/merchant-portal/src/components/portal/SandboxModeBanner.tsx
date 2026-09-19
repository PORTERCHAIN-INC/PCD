"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { integrationsApi } from "@/lib/integrations";

/** Sticky TEST MODE chrome when org preference is sandbox (UX-1). */
export default function SandboxModeBanner() {
  const { getApiToken, orgId } = useMerchantAuth();
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      if (!getApiToken) return;
      try {
        const token = await getApiToken();
        const row = await integrationsApi.sandbox(token, orgId);
        if (!cancelled) setEnabled(Boolean(row.sandbox_mode));
      } catch {
        if (!cancelled) setEnabled(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [getApiToken, orgId]);

  if (!enabled) return null;

  return (
    <div
      role="status"
      className="border-b border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950"
    >
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2">
        <p>
          <span className="font-semibold">Test mode preference on</span>
          {" — "}
          bookings you mark as Test do not dispatch a driver. Live bookings still book real
          capacity.
        </p>
        <Link
          href="/api?tab=sandbox"
          className="shrink-0 rounded-lg border border-amber-400 bg-white px-2.5 py-1 text-xs font-medium hover:bg-amber-100"
        >
          Sandbox settings
        </Link>
      </div>
    </div>
  );
}
