"use client";

import Script from "next/script";
import { useEffect } from "react";
import { useDeferUntilInteraction } from "@/lib/defer-until-interaction";
import { flushQueuedAnalyticsEvents, setAnalyticsProvider } from "@/lib/seo/analytics";

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
  }
}

const measurementId = (process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID ?? "").trim();

export default function GoogleAnalytics() {
  const ready = useDeferUntilInteraction(12_000);

  useEffect(() => {
    if (!measurementId || !ready) return;
    setAnalyticsProvider((event, properties) => {
      window.gtag?.("event", event, properties);
    });
    flushQueuedAnalyticsEvents();
  }, [ready]);

  if (!measurementId || !ready) return null;

  return (
    <>
      <Script
        src={`https://www.googletagmanager.com/gtag/js?id=${measurementId}`}
        strategy="afterInteractive"
      />
      <Script id="porterchain-ga4" strategy="afterInteractive">
        {`
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());
          gtag('config', '${measurementId}', { send_page_view: true });
        `}
      </Script>
    </>
  );
}
