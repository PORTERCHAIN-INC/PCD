"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import {
  DEFAULT_CONSENT,
  ensureGoogleConsentDefaults,
  type ConsentState,
} from "@/lib/marketing/consent";
import CookieConsentBanner from "@/components/marketing/CookieConsentBanner";

const GoogleAnalytics = dynamic(() => import("@/components/seo/GoogleAnalytics"), { ssr: false });
const WebVitalsReporter = dynamic(() => import("@/components/seo/WebVitalsReporter"), {
  ssr: false,
});
const CapacityGuideWidget = dynamic(() => import("@/components/home/CapacityGuideWidget"), {
  ssr: false,
});
const MarketingTags = dynamic(() => import("@/components/marketing/MarketingTags"), { ssr: false });

/**
 * Site-wide deferred integrations + CMP.
 * Logistics chat widget is available on all pages except home (inline) and login.
 * Analytics / marketing / experience tags respect Consent Mode.
 */
export default function DeferredSiteIntegrations() {
  const [consent, setConsent] = useState<ConsentState>(DEFAULT_CONSENT);

  const onConsentChange = useCallback((next: ConsentState) => {
    setConsent(next);
  }, []);

  useEffect(() => {
    ensureGoogleConsentDefaults();
  }, []);

  return (
    <>
      <WebVitalsReporter />
      <CapacityGuideWidget />
      <GoogleAnalytics enabled={consent.analytics} />
      <MarketingTags consent={consent} />
      <CookieConsentBanner onConsentChange={onConsentChange} />
    </>
  );
}
