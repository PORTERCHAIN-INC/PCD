"use client";

import { useEffect, useState } from "react";
import Script from "next/script";
import { publicEnv } from "@/lib/env";
import { useDeferUntilInteraction } from "@/lib/defer-until-interaction";
import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";
import { getStoredAttribution } from "@/lib/seo/attribution";
import { pushAttributionToZoho } from "@/lib/seo/zoho-attribution";
import "@/lib/seo/zoho-attribution";

const ZOHO_SALESIQ_INIT_SCRIPT = `
window.$zoho=window.$zoho||{};
$zoho.salesiq=$zoho.salesiq||{ready:function(){}};
`;

/**
 * Zoho SalesIQ live chat — loads after user interaction (or timeout) so the widget
 * cannot compete with LCP / first paint on marketing pages.
 */
export default function ZohoSalesIQ() {
  const { zohoSalesIqEnabled, zohoSalesIqWidgetCode } = publicEnv;
  const [hydrated, setHydrated] = useState(false);
  const interactionReady = useDeferUntilInteraction(15_000);

  useEffect(() => {
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated || !interactionReady || !zohoSalesIqEnabled || !zohoSalesIqWidgetCode) return;

    const priorReady = window.$zoho?.salesiq?.ready;
    window.$zoho = window.$zoho ?? {};
    window.$zoho.salesiq = window.$zoho.salesiq ?? {};
    window.$zoho.salesiq.ready = function zohoSalesIqReady() {
      if (typeof priorReady === "function") {
        priorReady();
      }
      pushAttributionToZoho(getStoredAttribution());
      track(ANALYTICS_EVENTS.ZOHO_CHAT_READY, { source_section: "salesiq_widget" });
      try {
        window.$zoho?.salesiq?.floatwindow?.on?.("open", () => {
          pushAttributionToZoho(getStoredAttribution());
          track(ANALYTICS_EVENTS.ZOHO_CHAT_OPEN, { source_section: "salesiq_widget" });
        });
      } catch {
        /* widget API varies by plan */
      }
    };
  }, [hydrated, interactionReady, zohoSalesIqEnabled, zohoSalesIqWidgetCode]);

  if (!zohoSalesIqEnabled || !zohoSalesIqWidgetCode || !hydrated || !interactionReady) {
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
