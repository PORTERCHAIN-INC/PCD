"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { submitInquiry } from "@/lib/submit-inquiry";

export default function BlogNewsletter() {
  const t = useTranslations("blog.sidebar");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await submitInquiry({
        email: email.trim(),
        source: "website",
        source_page: "/blog",
        form: "newsletter",
        inquiry_type: "newsletter",
        message: "Newsletter subscription from blog sidebar",
      });
      setDone(true);
    } catch {
      setError(t("newsletterError"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-2xl border border-primary/[0.06] bg-white p-5">
      <h3 className="text-base font-semibold text-primary tracking-tight">
        {t("newsletterTitle")}
      </h3>
      <p className="mt-2 text-sm text-muted leading-relaxed">{t("newsletterSubtitle")}</p>
      {done ? (
        <div className="mt-4 flex items-center gap-2 text-sm text-secondary font-medium">
          <Check className="w-4 h-4" />
          {t("subscribed")}
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-4 space-y-2">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={t("emailPlaceholder")}
            className="w-full rounded-xl border border-primary/10 px-3.5 py-2.5 text-sm outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/15"
          />
          <button
            type="submit"
            disabled={loading}
            className={cn(
              "w-full py-2.5 rounded-xl bg-secondary text-white text-sm font-semibold",
              "hover:bg-[#1d4ed8] transition-colors disabled:opacity-50"
            )}
          >
            {loading ? t("subscribing") : t("subscribe")}
          </button>
          {error && (
            <p className="text-xs text-red-600" role="alert">
              {error}
            </p>
          )}
        </form>
      )}
    </div>
  );
}
