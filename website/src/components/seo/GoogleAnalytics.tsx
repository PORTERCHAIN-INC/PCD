"use client";

import Script from "next/script";
import { useEffect } from "react";
import { useDeferUntilInteraction } from "@/lib/defer-until-interaction";
import { flushQueuedAnalyticsEvents, setAnalyticsProvider } from "@/lib/seo/analytics";
import { ensureGoogleConsentDefaults } from "@/lib/marketing/consent";
import { marketingPublicEnv } from "@/lib/marketing/config";

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
  }
}

type Props = {
  /** Analytics category granted via CMP */
  enabled: boolean;
};

export default function GoogleAnalytics({ enabled }: Props) {
  const ready = useDeferUntilInteraction(12_000);
  const measurementId = marketingPublicEnv.gaMeasurementId;
  // Skip direct GA when GTM owns tags
  const loadDirect = enabled && Boolean(measurementId) && !marketingPublicEnv.useGtmForMarketing;

  useEffect(() => {
    ensureGoogleConsentDefaults();
  }, []);

  useEffect(() => {
    if (!loadDirect || !ready) return;
    setAnalyticsProvider((event, properties) => {
      window.gtag?.("event", event, properties);
    });
    flushQueuedAnalyticsEvents();
  }, [loadDirect, ready]);

  if (!loadDirect || !ready) return null;

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
