"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { isMobilePhoneBrowser } from "@/lib/device";

const GoogleAnalytics = dynamic(() => import("@/components/seo/GoogleAnalytics"), { ssr: false });
const WebVitalsReporter = dynamic(() => import("@/components/seo/WebVitalsReporter"), {
  ssr: false,
});
const ZohoSalesIQ = dynamic(() => import("@/components/integrations/ZohoSalesIQ"), { ssr: false });
const MobileWhatsAppChat = dynamic(() => import("@/components/integrations/MobileWhatsAppChat"), {
  ssr: false,
});

/**
 * Site-wide deferred integrations.
 * Phone browsers get WhatsApp chat; desktop/tablet keep Zoho SalesIQ.
 */
export default function DeferredSiteIntegrations() {
  const [isPhone, setIsPhone] = useState<boolean | null>(null);

  useEffect(() => {
    setIsPhone(isMobilePhoneBrowser());
  }, []);

  return (
    <>
      <WebVitalsReporter />
      {isPhone === true ? <MobileWhatsAppChat /> : null}
      {isPhone === false ? <ZohoSalesIQ /> : null}
      <GoogleAnalytics />
    </>
  );
}
