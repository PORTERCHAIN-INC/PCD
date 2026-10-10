"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import {
  applyGoogleConsentMode,
  DEFAULT_CONSENT,
  readStoredConsent,
  writeStoredConsent,
  type ConsentState,
} from "@/lib/marketing/consent";

type Props = {
  onConsentChange: (consent: ConsentState) => void;
};

export default function CookieConsentBanner({ onConsentChange }: Props) {
  const t = useTranslations("marketing.consent");
  const [visible, setVisible] = useState(false);
  const [analytics, setAnalytics] = useState(false);
  const [marketing, setMarketing] = useState(false);
  const [experience, setExperience] = useState(false);
  // Mobile: categories collapse behind "Customize" so the banner covers less of the
  // viewport. Reject and Accept stay one tap away with equal size (Law 25 / GDPR).
  const [showPrefs, setShowPrefs] = useState(false);
  const pathname = usePathname() ?? "";
  const transactional = /^\/(en|fr)\/(book|track|email-preferences)(\/|$)/.test(pathname);

  useEffect(() => {
    const stored = readStoredConsent();
    if (stored) {
      onConsentChange(stored);
      setVisible(false);
      return;
    }
    onConsentChange(DEFAULT_CONSENT);
    setVisible(true);
  }, [onConsentChange]);

  function persist(next: { analytics: boolean; marketing: boolean; experience: boolean }) {
    const saved = writeStoredConsent(next);
    applyGoogleConsentMode(saved);
    onConsentChange(saved);
    setVisible(false);
  }

  if (!visible) return null;

  // Checkout / tracking / preferences pages have their own sticky primary action at the bottom
  // (Pay, Cancel, Save). There the banner is a compact strip parked ABOVE that action bar so the
  // one thing the user came to do is never covered. Reject and Accept stay equal and one tap.
  if (transactional) {
    return (
      <div
        role="dialog"
        aria-labelledby="pc-consent-title"
        data-testid="consent-compact"
        className="fixed inset-x-3 bottom-[calc(6rem+env(safe-area-inset-bottom))] z-[80] rounded-2xl border border-primary/10 bg-white px-4 py-3 shadow-premium sm:inset-x-auto sm:bottom-6 sm:right-6 sm:max-w-sm"
      >
        <p id="pc-consent-title" className="text-xs leading-snug text-primary/85">
          {t("description")}{" "}
          <Link href="/cookies" className="font-semibold text-secondary underline">
            {t("policyLink")}
          </Link>
        </p>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => persist({ analytics: false, marketing: false, experience: false })}
            className="min-h-[2.5rem] rounded-xl border border-primary/20 text-xs font-semibold text-primary"
          >
            {t("reject")}
          </button>
          <button
            type="button"
            onClick={() => persist({ analytics: true, marketing: true, experience: true })}
            className="min-h-[2.5rem] rounded-xl border border-primary/20 text-xs font-semibold text-primary"
          >
            {t("accept")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      role="dialog"
      aria-labelledby="pc-consent-title"
      aria-describedby="pc-consent-desc"
      className="fixed inset-x-0 bottom-0 z-[80] border-t border-primary/10 bg-white/95 px-4 py-3 shadow-premium backdrop-blur-md sm:p-5"
    >
      <div className="mx-auto flex max-w-5xl flex-col gap-3 sm:gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0 flex-1">
          <h2 id="pc-consent-title" className="text-sm font-semibold text-primary">
            {t("title")}
          </h2>
          <p
            id="pc-consent-desc"
            className="mt-1 text-xs leading-snug text-primary/80 sm:leading-relaxed"
          >
            {t("description")}{" "}
            <Link href="/cookies" className="font-medium text-secondary hover:underline">
              {t("policyLink")}
            </Link>
          </p>
          <div
            id="pc-consent-prefs"
            className={`mt-3 flex-wrap gap-4 text-xs text-primary ${showPrefs ? "flex" : "hidden sm:flex"}`}
          >
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked
                disabled
                readOnly
                className="rounded border-primary/20"
              />
              {t("necessary")}
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={analytics}
                onChange={(e) => setAnalytics(e.target.checked)}
                className="rounded border-primary/20"
              />
              {t("analytics")}
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={marketing}
                onChange={(e) => setMarketing(e.target.checked)}
                className="rounded border-primary/20"
              />
              {t("marketing")}
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={experience}
                onChange={(e) => setExperience(e.target.checked)}
                className="rounded border-primary/20"
              />
              {t("experience")}
            </label>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 sm:flex sm:flex-wrap shrink-0">
          <button
            type="button"
            onClick={() => persist({ analytics: false, marketing: false, experience: false })}
            className="min-h-[2.75rem] rounded-xl border border-primary/20 px-3 py-2 text-xs font-semibold text-primary hover:bg-gray-bg sm:px-4"
          >
            {t("reject")}
          </button>
          {showPrefs ? null : (
            <button
              type="button"
              onClick={() => setShowPrefs(true)}
              aria-controls="pc-consent-prefs"
              aria-expanded={false}
              className="min-h-[2.75rem] rounded-xl border border-primary/20 px-3 py-2 text-xs font-semibold text-primary hover:bg-gray-bg sm:hidden"
            >
              {t("customize")}
            </button>
          )}
          <button
            type="button"
            onClick={() => persist({ analytics, marketing, experience })}
            className={`min-h-[2.75rem] rounded-xl border border-primary/20 px-3 py-2 text-xs font-semibold text-primary hover:bg-gray-bg sm:inline-flex sm:items-center sm:px-4 ${showPrefs ? "" : "hidden"}`}
          >
            {t("save")}
          </button>
          <button
            type="button"
            onClick={() => persist({ analytics: true, marketing: true, experience: true })}
            className="min-h-[2.75rem] rounded-xl bg-secondary px-3 py-2 text-xs font-semibold text-white hover:bg-[#1d4ed8] sm:px-4"
          >
            {t("accept")}
          </button>
        </div>
      </div>
    </div>
  );
}
