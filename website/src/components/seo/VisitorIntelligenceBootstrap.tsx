"use client";

/**
 * Site-wide first-party visitor intelligence bootstrap.
 * Captures attribution + page journey; no fingerprinting / no third-party ID sync.
 */

import { useEffect } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { getOrCreateVisitorId, rememberQuoteIntent, recordPageView } from "@/lib/visitor-tracking";

export default function VisitorIntelligenceBootstrap() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    getOrCreateVisitorId();
    const intent = searchParams.get("intent") ?? undefined;
    const from = searchParams.get("from") ?? undefined;
    const vehicle = searchParams.get("vehicle") ?? undefined;
    if (intent || from || vehicle) {
      rememberQuoteIntent({ intent, from, vehicle });
    }
    recordPageView(pathname);
  }, [pathname, searchParams]);

  return null;
}
