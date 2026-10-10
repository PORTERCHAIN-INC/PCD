"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Mail, ArrowRight } from "lucide-react";
import { subscribeNewsletter } from "@/lib/submit-inquiry";
import MarketingConsentCheckbox from "@/components/forms/MarketingConsentCheckbox";
import { useFormGuard } from "@/components/forms/useFormGuard";

/** The only interactive part of the footer — kept as a small client island. */
export default function FooterNewsletter() {
  const t = useTranslations("footer");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const locale = useLocale();
  const { guardFields, honeypotField } = useFormGuard();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const value = email.trim();
    if (!value) return;
    setLoading(true);
    setError(null);
    try {
      await subscribeNewsletter({
        email: value,
        source_page: "/footer-newsletter",
        locale,
        ...guardFields(),
      });
      setDone(true);
      setEmail("");
    } catch {
      setError(t("newsletterError"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="max-w-md">
        <h2 className="text-lg font-semibold text-white">{t("newsletterTitle")}</h2>
        <p className="mt-1 text-sm text-white/70">{t("newsletterSubtitle")}</p>
      </div>
      <form
        onSubmit={onSubmit}
        className="relative flex w-full max-w-md flex-col gap-2 sm:w-auto sm:flex-row sm:flex-wrap"
        suppressHydrationWarning
      >
        {done ? (
          <p className="py-3 text-sm font-medium text-[#93c5fd]" role="status">
            {t("subscribed")}
          </p>
        ) : (
          <>
            <label className="flex min-h-11 flex-1 items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 sm:w-72">
              <Mail className="h-4 w-4 shrink-0 text-white/60" aria-hidden />
              <span className="sr-only">{t("emailPlaceholder")}</span>
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t("emailPlaceholder")}
                className="h-11 min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-white/60"
              />
            </label>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full bg-secondary px-6 text-sm font-semibold text-white transition-colors hover:bg-[#1d4ed8] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white disabled:opacity-60"
            >
              {loading ? t("subscribing") : t("subscribe")}
              <ArrowRight className="h-4 w-4" aria-hidden />
            </button>
            {honeypotField}
            <div className="w-full sm:basis-full">
              <MarketingConsentCheckbox
                id="footer-newsletter-consent"
                tone="dark"
                required
                checked={consent}
                onChange={setConsent}
              />
            </div>
          </>
        )}
        {error ? (
          <p className="text-sm text-red-300" role="alert">
            {error}
          </p>
        ) : null}
      </form>
    </div>
  );
}
