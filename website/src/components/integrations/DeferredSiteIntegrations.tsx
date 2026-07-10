"use client";

import dynamic from "next/dynamic";

const GoogleAnalytics = dynamic(() => import("@/components/seo/GoogleAnalytics"), { ssr: false });
const ZohoSalesIQ = dynamic(() => import("@/components/integrations/ZohoSalesIQ"), { ssr: false });

export default function DeferredSiteIntegrations() {
  return (
    <>
      <ZohoSalesIQ />
      <GoogleAnalytics />
    </>
  );
}
