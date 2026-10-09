"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import {
  DEFAULT_CONSENT,
  ensureGoogleConsentDefaults,
  type ConsentState,
} from "@/lib/marketing/consent";
import CookieConsentBanner from "@/components/marketing/CookieConsentBanner";
import MobilePriceBar from "@/components/marketing/price/MobilePriceBar";

const GoogleAnalytics = dynamic(() => import("@/components/seo/GoogleAnalytics"), { ssr: false });
const WebVitalsReporter = dynamic(() => import("@/components/seo/WebVitalsReporter"), {
  ssr: false,
});
const CapacityGuideWidget = dynamic(
  () => import("@/components/marketing/home/CapacityGuideWidget"),
  {
    ssr: false,
  }
);
const MarketingTags = dynamic(() => import("@/components/marketing/MarketingTags"), { ssr: false });
const MobileWhatsAppChat = dynamic(() => import("@/components/integrations/MobileWhatsAppChat"), {
  ssr: false,
});
const VisitorIntelligenceBootstrap = dynamic(
  () => import("@/components/seo/VisitorIntelligenceBootstrap"),
  { ssr: false }
);

/** Load non-critical widgets on first interaction, or when the main thread is idle (max ~3 s). */
const IDLE_TIMEOUT_MS = 3000;
const INTERACTION_EVENTS = ["pointerdown", "keydown", "touchstart", "scroll"] as const;

function useIdleOrInteraction(): boolean {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let done = false;
    const go = () => {
      if (done) return;
      done = true;
      setReady(true);
    };
    const idle = window.requestIdleCallback
      ? window.requestIdleCallback(go, { timeout: IDLE_TIMEOUT_MS })
      : window.setTimeout(go, IDLE_TIMEOUT_MS);
    for (const name of INTERACTION_EVENTS) {
      window.addEventListener(name, go, { once: true, passive: true });
    }
    return () => {
      if (window.cancelIdleCallback) window.cancelIdleCallback(idle as number);
      else window.clearTimeout(idle as number);
      for (const name of INTERACTION_EVENTS) window.removeEventListener(name, go);
    };
  }, []);
  return ready;
}

/**
 * Site-wide deferred integrations + CMP.
 * Logistics chat widget is available on all pages except login / sign-up.
 * Analytics / marketing / experience tags respect Consent Mode (nothing loads before consent).
 * Visitor intelligence, the chat launcher and the WhatsApp button wait for idle / first
 * interaction so they never compete with the page's own content (LCP / TBT).
 * Phone browsers also get a floating WhatsApp chat button and the sticky "Get a price" bar.
 */
export default function DeferredSiteIntegrations() {
  const [consent, setConsent] = useState<ConsentState>(DEFAULT_CONSENT);
  const [showWhatsAppFab, setShowWhatsAppFab] = useState(false);
  const idleReady = useIdleOrInteraction();

  const onConsentChange = useCallback((next: ConsentState) => {
    setConsent(next);
  }, []);

  useEffect(() => {
    ensureGoogleConsentDefaults();
  }, []);

  useEffect(() => {
    if (!idleReady) return;
    let cancelled = false;
    void import("@/lib/device").then(({ isMobilePhoneBrowser }) => {
      if (!cancelled) setShowWhatsAppFab(isMobilePhoneBrowser());
    });
    return () => {
      cancelled = true;
    };
  }, [idleReady]);

  return (
    <>
      {idleReady ? (
        <Suspense fallback={null}>
          <VisitorIntelligenceBootstrap />
        </Suspense>
      ) : null}
      <WebVitalsReporter />
      {idleReady ? <CapacityGuideWidget /> : null}
      {idleReady && showWhatsAppFab ? <MobileWhatsAppChat /> : null}
      <MobilePriceBar />
      <GoogleAnalytics enabled={consent.analytics} />
      <MarketingTags consent={consent} />
      <CookieConsentBanner onConsentChange={onConsentChange} />
    </>
  );
}
