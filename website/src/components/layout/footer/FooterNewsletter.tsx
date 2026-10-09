"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Mail, ArrowRight } from "lucide-react";
import { submitInquiry } from "@/lib/submit-inquiry";

/** The only interactive part of the footer — kept as a small client island. */
export default function FooterNewsletter() {
  const t = useTranslations("footer");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const value = email.trim();
    if (!value) return;
    setLoading(true);
    setError(null);
    try {
      await submitInquiry({
        email: value,
        source: "website",
        source_page: "/footer-newsletter",
        form: "newsletter",
        inquiry_type: "newsletter",
        message: "Newsletter subscription from site footer",
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
        className="flex w-full max-w-md flex-col gap-2 sm:w-auto sm:flex-row"
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
