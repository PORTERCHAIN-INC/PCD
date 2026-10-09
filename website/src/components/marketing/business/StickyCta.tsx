"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { ArrowRight } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { quoteSignUpPath } from "@/data/portal-links";
import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";
import { cn } from "@/lib/utils";

/**
 * /business sticky quote bar — tablet / desktop only. Phones get the site-wide
 * MobilePriceBar instead (one sticky bar per screen). CSS transition, no framer-motion.
 */
export default function StickyCta() {
  const t = useTranslations("businessPage.stickyCta");
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 600);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div
      className={cn(
        "price-bar pointer-events-none fixed bottom-0 left-0 right-0 z-40 hidden px-4 pt-2 safe-bottom md:block",
        visible && "price-bar--on"
      )}
      aria-hidden={!visible}
    >
      <div className={cn("mx-auto max-w-lg", visible && "pointer-events-auto")}>
        <div className="biz-glass-dark biz-shadow-lg flex items-center justify-between gap-3 rounded-2xl px-4 py-3 sm:gap-4 sm:px-5 sm:py-3.5">
          <p className="hidden min-w-0 text-sm font-medium text-white sm:block">{t("message")}</p>
          <Link
            href={quoteSignUpPath({ from: "business-sticky" })}
            tabIndex={visible ? undefined : -1}
            onClick={() => {
              track(ANALYTICS_EVENTS.CTA_CLICK, {
                source_section: "business-sticky",
                path: "clerk_signup",
                cta_label: "sticky_quote",
              });
              track(ANALYTICS_EVENTS.QUOTE_REQUEST, {
                source_section: "business-sticky",
                path: "clerk_signup",
              });
            }}
            className="flex min-h-[2.75rem] w-full items-center justify-center gap-2 whitespace-nowrap rounded-xl bg-[#2563eb] px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#1d4ed8] sm:ml-auto sm:w-auto"
          >
            {t("button")}
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
