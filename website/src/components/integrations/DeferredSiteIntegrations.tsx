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
const MobileWhatsAppChat = dynamic(() => import("@/components/integrations/MobileWhatsAppChat"), {
  ssr: false,
});

/**
 * Site-wide deferred integrations + CMP.
 * Logistics chat widget is available on all pages except home (inline) and login.
 * Analytics / marketing / experience tags respect Consent Mode.
 * Phone browsers also get a floating WhatsApp chat button.
 */
export default function DeferredSiteIntegrations() {
  const [consent, setConsent] = useState<ConsentState>(DEFAULT_CONSENT);
  const [showWhatsAppFab, setShowWhatsAppFab] = useState(false);

  const onConsentChange = useCallback((next: ConsentState) => {
    setConsent(next);
  }, []);

  useEffect(() => {
    ensureGoogleConsentDefaults();
  }, []);

  useEffect(() => {
    let cancelled = false;
    void import("@/lib/device").then(({ isMobilePhoneBrowser }) => {
      if (!cancelled) setShowWhatsAppFab(isMobilePhoneBrowser());
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <WebVitalsReporter />
      <CapacityGuideWidget />
      {showWhatsAppFab ? <MobileWhatsAppChat /> : null}
      <GoogleAnalytics enabled={consent.analytics} />
      <MarketingTags consent={consent} />
      <CookieConsentBanner onConsentChange={onConsentChange} />
    </>
  );
}
