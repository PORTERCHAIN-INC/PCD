"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { Search } from "lucide-react";

export default function GuestTrackLookup({ compact = false }: { compact?: boolean }) {
  const t = useTranslations("portal.customer");
  const router = useRouter();
  const [tracking, setTracking] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const value = tracking.trim();
    if (!value) return;
    router.push(`/track/${encodeURIComponent(value)}`);
  };

  return (
    <section
      className={
        compact
          ? "rounded-2xl border border-primary/10 bg-gray-bg/80 p-5"
          : "rounded-2xl border border-primary/10 bg-gray-bg p-6"
      }
    >
      <h2 className={compact ? "type-body font-bold text-primary mb-1" : "type-h3 font-bold text-primary mb-2"}>
        {t("guestTrackTitle")}
      </h2>
      <p className="type-caption text-muted mb-4">{t("guestTrackSubtitle")}</p>
      <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row">
        <input
          value={tracking}
          onChange={(e) => setTracking(e.target.value)}
          placeholder={t("guestTrackPlaceholder")}
          className="flex-1 rounded-xl border border-primary/10 bg-white px-4 py-3 type-small font-mono"
          autoComplete="off"
        />
        <button
          type="submit"
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-white font-semibold type-small hover:bg-primary/90"
        >
          <Search className="h-4 w-4" aria-hidden />
          {t("guestTrackSubmit")}
        </button>
      </form>
    </section>
  );
}
