#!/usr/bin/env python3
"""Wave 10 w10-5 guard — WhatsApp pre-filled deep links on quote confirmation."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WHATSAPP = ROOT / "website/src/lib/whatsapp.ts"
LINK = ROOT / "website/src/components/seo/WhatsAppQuoteLink.tsx"
CONTACT = ROOT / "website/src/components/corporate/sections/ContactInquiryForm.tsx"
BUSINESS = ROOT / "website/src/components/business/InquiryForm.tsx"
ANALYTICS = ROOT / "website/src/lib/seo/analytics.ts"
DEVICE = ROOT / "website/src/lib/device.ts"
DEFERRED = ROOT / "website/src/components/integrations/DeferredSiteIntegrations.tsx"
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
        failures.append("ContactInquiryForm missing WhatsApp quote success CTA")

    business = BUSINESS.read_text(encoding="utf-8")
    if "WhatsAppQuoteLink" not in business:
        failures.append("InquiryForm missing WhatsApp quote success CTA")

    analytics = ANALYTICS.read_text(encoding="utf-8")
    if "WHATSAPP_QUOTE_CLICK" not in analytics:
        failures.append("analytics.ts missing WHATSAPP_QUOTE_CLICK event")
    if "WHATSAPP_CHAT_CLICK" not in analytics:
        failures.append("analytics.ts missing WHATSAPP_CHAT_CLICK event")

    device = DEVICE.read_text(encoding="utf-8")
    if "isMobilePhoneBrowser" not in device:
        failures.append("device.ts missing isMobilePhoneBrowser")

    deferred = DEFERRED.read_text(encoding="utf-8")
    if "MobileWhatsAppChat" not in deferred or "isMobilePhoneBrowser" not in deferred:
        failures.append("DeferredSiteIntegrations missing mobile WhatsApp vs Zoho split")
    if "ZohoSalesIQ" not in deferred:
        failures.append("DeferredSiteIntegrations missing ZohoSalesIQ for non-phone")

    mobile_chat = MOBILE_CHAT.read_text(encoding="utf-8")
    if "buildWhatsAppDeepLink" not in mobile_chat or "WHATSAPP_CHAT_CLICK" not in mobile_chat:
        failures.append("MobileWhatsAppChat missing deep link or tracking")

    print("Wave 10 w10-5 guard (WhatsApp quote confirmation + mobile chat)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: pre-filled wa.me on contact + business quote success; phone FAB vs Zoho")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
