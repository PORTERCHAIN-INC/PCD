"use client";

import Script from "next/script";
import { publicEnv } from "@/lib/env";

/**
 * Zoho SalesIQ live chat — loads when NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED=true
 * and NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE is set in website/.env.local
 */
export default function ZohoSalesIQ() {
  const { zohoSalesIqEnabled, zohoSalesIqWidgetCode } = publicEnv;

  if (!zohoSalesIqEnabled || !zohoSalesIqWidgetCode) {
    return null;
  }

  const widgetCode = zohoSalesIqWidgetCode;

  return (
    <>
      <Script id="zoho-salesiq-init" strategy="afterInteractive">
        {`window.$zoho=window.$zoho||{};$zoho.salesiq=$zoho.salesiq||{ready:function(){}};`}
      </Script>
      <Script
        id="zsiqscript"
        src={`https://salesiq.zohopublic.com/widget?wc=${widgetCode}`}
        strategy="lazyOnload"
        defer
      />
    </>
  );
}
