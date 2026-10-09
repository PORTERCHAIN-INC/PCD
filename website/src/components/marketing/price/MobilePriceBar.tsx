"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { ArrowRight } from "lucide-react";
import { Link, usePathname } from "@/i18n/navigation";
import { HOME_PRICE_ANCHOR_ID, isPriceBarHidden } from "@/lib/marketing/price-bar";
import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";
import { cn } from "@/lib/utils";

const SCROLL_THRESHOLD_PX = 480;

/**
 * Sticky mobile "Get a price" bar (phones only, `md:hidden`).
 * - Home: appears once the hero calculator scrolls out of view; tapping scrolls back to it.
 * - Elsewhere: appears after the first screen; links to the delivery cost calculator.
 * While visible it sets `html[data-price-bar="on"]` so the chat / WhatsApp launchers lift above it.
 */
export default function MobilePriceBar() {
  const t = useTranslations("marketing.priceBar");
  const pathname = usePathname() || "/";
  const hidden = isPriceBarHidden(pathname);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (hidden) {
      setVisible(false);
      return;
    }
    const anchor = document.getElementById(HOME_PRICE_ANCHOR_ID);
    if (anchor && "IntersectionObserver" in window) {
      const io = new IntersectionObserver(
        ([entry]) => setVisible(!entry.isIntersecting && entry.boundingClientRect.top < 0),
        { threshold: 0 }
      );
      io.observe(anchor);
      return () => io.disconnect();
    }
    const onScroll = () => setVisible(window.scrollY > SCROLL_THRESHOLD_PX);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, [hidden, pathname]);

  useEffect(() => {
    const root = document.documentElement;
    if (visible) root.dataset.priceBar = "on";
    else delete root.dataset.priceBar;
    return () => {
      delete root.dataset.priceBar;
    };
  }, [visible]);

  if (hidden) return null;

  const onHome = pathname === "/";

  function onClick(event: React.MouseEvent<HTMLAnchorElement>) {
    track(ANALYTICS_EVENTS.CTA_CLICK, {
      source_section: "mobile_price_bar",
      cta_label: "get_a_price",
      path: pathname,
    });
    if (!onHome) return;
    const anchor = document.getElementById(HOME_PRICE_ANCHOR_ID);
    if (!anchor) return;
    event.preventDefault();
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    anchor.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    anchor.querySelector<HTMLInputElement>("input")?.focus({ preventScroll: true });
  }

  return (
    <div
      className={cn(
        "price-bar fixed inset-x-0 bottom-0 z-[55] md:hidden",
        visible ? "price-bar--on" : "pointer-events-none"
      )}
      aria-hidden={!visible}
    >
      <div className="flex items-center gap-3 border-t border-primary/10 bg-white/95 px-4 pt-2.5 pb-[max(0.625rem,env(safe-area-inset-bottom))] shadow-[0_-8px_24px_rgba(11,18,32,0.08)] backdrop-blur-md">
        <p className="min-w-0 flex-1 text-sm font-medium leading-tight text-primary">
          {t("label")}
        </p>
        <Link
          href={`/delivery-cost-calculator`}
          onClick={onClick}
          tabIndex={visible ? undefined : -1}
          className="inline-flex min-h-[2.75rem] shrink-0 items-center gap-1.5 rounded-full bg-secondary px-5 text-sm font-semibold text-white shadow-sm hover:bg-[#1a47bf] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2"
        >
          {t("cta")}
          <ArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      </div>
    </div>
  );
}
