#!/usr/bin/env python3
"""Wave 10 w10-5 guard — WhatsApp pre-filled deep links + site logistics chat widget."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WHATSAPP = ROOT / "website/src/lib/whatsapp.ts"
LINK = ROOT / "website/src/components/seo/WhatsAppQuoteLink.tsx"
CONTACT = ROOT / "website/src/app/[locale]/contact/page.tsx"
NAVBAR = ROOT / "website/src/components/layout/SiteNavbar.tsx"
ANALYTICS = ROOT / "website/src/lib/seo/analytics.ts"
DEFERRED = ROOT / "website/src/components/integrations/DeferredSiteIntegrations.tsx"
WIDGET = ROOT / "website/src/components/marketing/home/CapacityGuideWidget.tsx"
MOBILE_CHAT = ROOT / "website/src/components/integrations/MobileWhatsAppChat.tsx"


def main() -> int:
    failures: list[str] = []

    wa = WHATSAPP.read_text(encoding="utf-8")
    if "buildWhatsAppDeepLink" not in wa or "buildQuoteWhatsAppMessage" not in wa:
        failures.append("whatsapp.ts missing deep link helpers")
    if "buildChatWhatsAppMessage" not in wa:
        failures.append("whatsapp.ts missing mobile chat prefill helper")

    link = LINK.read_text(encoding="utf-8")
    if "WhatsAppQuoteLink" not in link or "WHATSAPP_QUOTE_CLICK" not in link:
        failures.append("WhatsAppQuoteLink.tsx missing component or tracking")

    contact = CONTACT.read_text(encoding="utf-8")
    if "WhatsAppQuoteLink" not in contact or "buildQuoteWhatsAppMessage" not in contact:
        failures.append("contact page missing WhatsApp quote CTA")

    navbar = NAVBAR.read_text(encoding="utf-8")
    if "buildWhatsAppDeepLink" not in navbar:
        failures.append("SiteNavbar missing WhatsApp deep link")

    analytics = ANALYTICS.read_text(encoding="utf-8")
    if "WHATSAPP_QUOTE_CLICK" not in analytics:
        failures.append("analytics.ts missing WHATSAPP_QUOTE_CLICK event")
    if "CAPACITY_GUIDE_WIDGET_OPEN" not in analytics:
        failures.append("analytics.ts missing CAPACITY_GUIDE_WIDGET_OPEN event")

    deferred = DEFERRED.read_text(encoding="utf-8")
    if "CapacityGuideWidget" not in deferred:
        failures.append("DeferredSiteIntegrations missing CapacityGuideWidget")
    if "ZohoSalesIQ" in deferred:
        failures.append("DeferredSiteIntegrations must not load ZohoSalesIQ")

    if not WIDGET.is_file():
        failures.append("missing CapacityGuideWidget.tsx")
    else:
        widget = WIDGET.read_text(encoding="utf-8")
        if "CapacityGuideChat" not in widget:
            failures.append("CapacityGuideWidget must wrap CapacityGuideChat")
        if "isCapacityGuideFabHidden" not in widget:
            failures.append("CapacityGuideWidget must use isCapacityGuideFabHidden")

    if MOBILE_CHAT.is_file():
        mobile_chat = MOBILE_CHAT.read_text(encoding="utf-8")
        if "buildWhatsAppDeepLink" not in mobile_chat or "WHATSAPP_CHAT_CLICK" not in mobile_chat:
            failures.append("MobileWhatsAppChat missing deep link or tracking")
        if "MOBILE_WHATSAPP_FAB_OFFSET_ABOVE_GUIDE" not in mobile_chat:
            failures.append("MobileWhatsAppChat must offset above Capacity Guide FAB")

    fab_helper = ROOT / "website/src/lib/capacity-guide-fab.ts"
    if not fab_helper.is_file():
        failures.append("missing capacity-guide-fab.ts")
    else:
        fab = fab_helper.read_text(encoding="utf-8")
        if "isCapacityGuideFabHidden" not in fab:
            failures.append("capacity-guide-fab.ts missing isCapacityGuideFabHidden")

    print("Wave 10 w10-5 guard (WhatsApp quote confirmation + site logistics chat)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: wa.me quote CTAs; CapacityGuideWidget sitewide; no Zoho chat")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
