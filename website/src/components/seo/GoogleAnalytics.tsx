"use client";

import Script from "next/script";
import { useEffect } from "react";
import { setAnalyticsProvider } from "@/lib/seo/analytics";

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
    $zoho?: {
      salesiq?: {
        ready?: () => void;
        floatwindow?: { on?: (event: string, cb: () => void) => void };
      };
    };
  }
}

const measurementId = (process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID ?? "").trim();

export default function GoogleAnalytics() {
  useEffect(() => {
    if (!measurementId) return;
    setAnalyticsProvider((event, properties) => {
      window.gtag?.("event", event, properties);
    });
  }, []);

  if (!measurementId) return null;

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
