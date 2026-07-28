"use client";

import { useEffect, useState } from "react";
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

  return (
    <div
      role="dialog"
      aria-labelledby="pc-consent-title"
      aria-describedby="pc-consent-desc"
      className="fixed inset-x-0 bottom-0 z-[80] border-t border-primary/10 bg-white/95 p-4 shadow-premium backdrop-blur-md sm:p-5"
    >
      <div className="mx-auto flex max-w-5xl flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0 flex-1">
          <h2 id="pc-consent-title" className="text-sm font-semibold text-primary">
            {t("title")}
          </h2>
          <p id="pc-consent-desc" className="mt-1 text-xs leading-relaxed text-muted">
            {t("description")}{" "}
            <Link href="/cookies" className="font-medium text-secondary hover:underline">
              {t("policyLink")}
            </Link>
          </p>
          <div className="mt-3 flex flex-wrap gap-4 text-xs text-primary">
            <label className="inline-flex items-center gap-2">
              <input type="checkbox" checked disabled className="rounded border-primary/20" />
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
        <div className="flex flex-wrap gap-2 shrink-0">
          <button
            type="button"
            onClick={() => persist({ analytics: false, marketing: false, experience: false })}
            className="rounded-xl border border-primary/10 px-4 py-2.5 text-xs font-medium text-primary hover:bg-gray-bg"
          >
            {t("reject")}
          </button>
          <button
            type="button"
            onClick={() => persist({ analytics, marketing, experience })}
            className="rounded-xl border border-primary/10 px-4 py-2.5 text-xs font-medium text-primary hover:bg-gray-bg"
          >
            {t("save")}
          </button>
          <button
            type="button"
            onClick={() => persist({ analytics: true, marketing: true, experience: true })}
            className="rounded-xl bg-secondary px-4 py-2.5 text-xs font-semibold text-white hover:bg-[#1d4ed8]"
          >
            {t("accept")}
          </button>
        </div>
      </div>
    </div>
  );
}
