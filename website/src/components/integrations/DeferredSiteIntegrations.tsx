"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { isMobilePhoneBrowser } from "@/lib/device";
import { isZohoSalesIqConfigured } from "@/lib/env";
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
const ZohoSalesIQ = dynamic(() => import("@/components/integrations/ZohoSalesIQ"), { ssr: false });
const MobileWhatsAppChat = dynamic(() => import("@/components/integrations/MobileWhatsAppChat"), {
  ssr: false,
});
const MarketingTags = dynamic(() => import("@/components/marketing/MarketingTags"), { ssr: false });

/**
 * Site-wide deferred integrations + CMP.
 * Phone browsers get WhatsApp chat; desktop/tablet keep Zoho SalesIQ (chat category ≈ necessary UX).
 * Analytics / marketing / experience tags respect Consent Mode.
 */
export default function DeferredSiteIntegrations() {
  const [isPhone, setIsPhone] = useState<boolean | null>(null);
  const [consent, setConsent] = useState<ConsentState>(DEFAULT_CONSENT);

  const onConsentChange = useCallback((next: ConsentState) => {
    setConsent(next);
  }, []);

  useEffect(() => {
    ensureGoogleConsentDefaults();
    setIsPhone(isMobilePhoneBrowser());
  }, []);

  const chatOk = isZohoSalesIqConfigured();

  return (
    <>
      <WebVitalsReporter />
      {isPhone === true ? <MobileWhatsAppChat /> : null}
      {isPhone === false && chatOk ? <ZohoSalesIQ /> : null}
      <GoogleAnalytics enabled={consent.analytics} />
      <MarketingTags consent={consent} />
      <CookieConsentBanner onConsentChange={onConsentChange} />
    </>
  );
}
