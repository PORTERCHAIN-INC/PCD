"use client";

import { useMemo } from "react";
import { FaWhatsapp } from "react-icons/fa6";
import { useLocale, useTranslations } from "next-intl";
import { usePathname } from "next/navigation";
import {
  isCapacityGuideFabHidden,
  MOBILE_FAB_BOTTOM_DEFAULT,
  MOBILE_WHATSAPP_FAB_OFFSET_ABOVE_GUIDE,
} from "@/lib/capacity-guide-fab";
import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";
import { getOrCreateVisitorId } from "@/lib/visitor-tracking";
import { buildChatWhatsAppMessage, buildWhatsAppDeepLink } from "@/lib/whatsapp";

/**
 * Floating WhatsApp chat button for phone browsers.
 * Desktop/tablet use the on-site Logistics / Capacity line instead of a third-party widget.
 * Prefill includes UTM + visitor claim code so staff can attribute the thread.
 * Sits above the Capacity Guide FAB when that launcher is visible (same corner).
 */
export default function MobileWhatsAppChat() {
  const t = useTranslations("corporate.contact.info.whatsappChat");
  const locale = useLocale();
  const pathname = usePathname();
  const guideFabVisible = !isCapacityGuideFabHidden(pathname || "/");
  const href = useMemo(() => {
    let visitorId = "";
    try {
      visitorId = getOrCreateVisitorId();
    } catch {
      visitorId = "";
    }
    const params =
      typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
    return buildWhatsAppDeepLink(
      buildChatWhatsAppMessage({
        locale,
        visitorId,
        path: pathname || undefined,
        utmSource: params?.get("utm_source") || "whatsapp",
        utmMedium: params?.get("utm_medium") || "fab",
        utmCampaign: params?.get("utm_campaign") || "capacity_chat",
      })
    );
  }, [locale, pathname]);

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={t("ariaLabel")}
      className="pc-fab fixed z-[61] flex h-14 w-14 items-center justify-center rounded-full bg-[#25D366] text-white shadow-lg transition-transform hover:scale-105 active:scale-95"
      style={{
        right: "max(1rem, env(safe-area-inset-right, 0px))",
        bottom: guideFabVisible
          ? MOBILE_WHATSAPP_FAB_OFFSET_ABOVE_GUIDE
          : MOBILE_FAB_BOTTOM_DEFAULT,
      }}
      onClick={() =>
        track(ANALYTICS_EVENTS.WHATSAPP_CHAT_CLICK, {
          source_section: "mobile_chat_fab",
        })
      }
    >
      <FaWhatsapp className="h-7 w-7" aria-hidden />
    </a>
  );
}
