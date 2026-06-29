"use client";

import Script from "next/script";
import { publicEnv } from "@/lib/env";

const ZOHO_SALESIQ_INIT_SCRIPT = `
window.$zoho=window.$zoho||{};
$zoho.salesiq=$zoho.salesiq||{ready:function(){}};
`;

/**
 * Zoho SalesIQ live chat — loads when NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED=true
 * and NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE is set in website/.env.local.
 * Uses Zoho's default (natural) chat appearance.
 */
export default function ZohoSalesIQ() {
  const { zohoSalesIqEnabled, zohoSalesIqWidgetCode } = publicEnv;

  if (!zohoSalesIqEnabled || !zohoSalesIqWidgetCode) {
    return null;
  }

  return (
    <>
      <Script id="zoho-salesiq-init" strategy="afterInteractive">
        {ZOHO_SALESIQ_INIT_SCRIPT}
      </Script>
      <Script
        id="zsiqscript"
        src={`https://salesiq.zohopublic.ca/widget?wc=${zohoSalesIqWidgetCode}`}
        strategy="afterInteractive"
      />
    </>
  );
}
