"use client";

import { MessageCircle, X } from "lucide-react";
import { useEffect, useId, useState } from "react";
import { useTranslations } from "next-intl";
import CapacityGuideChat from "@/components/home/CapacityGuideChat";
import { usePathname } from "@/i18n/navigation";
import { OPEN_LOGISTICS_CHAT_EVENT } from "@/lib/home/open-logistics-chat";
import { ANALYTICS_EVENTS, track } from "@/lib/seo/analytics";
import { cn } from "@/lib/utils";

/** Routes where the floating launcher is hidden (inline chat or auth). */
function shouldHideLauncher(pathname: string): boolean {
  if (pathname === "/" || pathname === "") return true;
  if (pathname.startsWith("/login")) return true;
  return false;
}

/**
 * Site-wide Logistics line — FAB + panel on every page except home (inline) and login.
 * Shares sessionStorage with the homepage chat. One chat instance stays mounted after first open.
 */
export default function CapacityGuideWidget() {
  const t = useTranslations("homeChooser.guide");
  const pathname = usePathname();
  const panelId = useId();
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  const hidden = shouldHideLauncher(pathname);

  useEffect(() => {
    if (hidden) setOpen(false);
  }, [hidden]);

  useEffect(() => {
    function onOpen() {
      if (hidden) return;
      setMounted(true);
      setOpen(true);
    }
    window.addEventListener(OPEN_LOGISTICS_CHAT_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_LOGISTICS_CHAT_EVENT, onOpen);
  }, [hidden]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  function openPanel() {
    setMounted(true);
    setOpen(true);
    track(ANALYTICS_EVENTS.CAPACITY_GUIDE_WIDGET_OPEN, {
      sourceSection: "site-capacity-guide-widget",
      cta_label: "open",
      path: pathname,
    });
  }

  function closePanel() {
    setOpen(false);
  }

  if (hidden) return null;

  return (
    <div
      className="pointer-events-none fixed z-[60] flex flex-col items-end"
      style={{
        right: "max(1rem, env(safe-area-inset-right, 0px))",
        bottom: "max(1.25rem, calc(1rem + env(safe-area-inset-bottom, 0px)))",
      }}
    >
      {mounted ? (
        <div
          id={panelId}
          className={cn(
            "pointer-events-auto mb-3 w-[min(24rem,calc(100vw-2rem))] transition-[opacity,transform] duration-200",
            open
              ? "translate-y-0 opacity-100"
              : "pointer-events-none invisible absolute bottom-16 translate-y-2 opacity-0"
          )}
          aria-hidden={!open}
        >
          <CapacityGuideChat
            onClose={closePanel}
            sourceSection="site-capacity-guide-widget"
            className="h-[min(32rem,calc(100dvh-6.5rem))] max-h-[70dvh] rounded-2xl bg-[#070d18]/96 shadow-[0_28px_80px_rgba(0,0,0,0.5)]"
          />
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => (open ? closePanel() : openPanel())}
        aria-expanded={open}
        aria-controls={mounted ? panelId : undefined}
        aria-label={open ? t("closeAria") : t("launcherAria")}
        className={cn(
          "pointer-events-auto relative flex h-14 w-14 items-center justify-center rounded-full",
          "bg-secondary text-white shadow-lg shadow-secondary/35 transition-transform",
          "hover:bg-[#1d4ed8] hover:scale-105 active:scale-95",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/80 focus-visible:ring-offset-2 focus-visible:ring-offset-primary"
        )}
      >
        <span className="sr-only">{open ? t("closeAria") : t("launcherLabel")}</span>
        {open ? (
          <X className="h-6 w-6" aria-hidden />
        ) : (
          <MessageCircle className="h-6 w-6" aria-hidden />
        )}
        {!open ? (
          <span
            className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-emerald-400 ring-2 ring-white"
            aria-hidden
          />
        ) : null}
      </button>
    </div>
  );
}
