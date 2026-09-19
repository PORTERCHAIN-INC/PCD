"use client";

import { useEffect } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { captureAttribution } from "@/lib/seo/attribution";
import { pushAttributionToZoho } from "@/lib/seo/zoho-attribution";

/** Capture UTM, `from=`, and landing context per session for GA4 + Zoho CRM tagging. */
export default function AttributionCapture() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    const attribution = captureAttribution();
    pushAttributionToZoho(attribution);
  }, [pathname, searchParams]);

  return null;
}
