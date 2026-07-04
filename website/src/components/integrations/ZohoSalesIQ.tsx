"use client";

import { useEffect, useState } from "react";
import Script from "next/script";
import { publicEnv } from "@/lib/env";

const ZOHO_SALESIQ_INIT_SCRIPT = `
window.$zoho=window.$zoho||{};
$zoho.salesiq=$zoho.salesiq||{ready:function(){}};
`;

/**
 * Zoho SalesIQ live chat — loads after React hydration so the widget cannot
 * mutate SSR markup (e.g. siq_id on forms) before hydrate.
 */
export default function ZohoSalesIQ() {
  const { zohoSalesIqEnabled, zohoSalesIqWidgetCode } = publicEnv;
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

  if (!zohoSalesIqEnabled || !zohoSalesIqWidgetCode || !hydrated) {
    return null;
  }

  return (
    <>
      <Script id="zoho-salesiq-init" strategy="lazyOnload">
        {ZOHO_SALESIQ_INIT_SCRIPT}
      </Script>
      <Script
        id="zsiqscript"
        src={`https://salesiq.zohopublic.ca/widget?wc=${zohoSalesIqWidgetCode}`}
        strategy="lazyOnload"
      />
    </>
  );
}
