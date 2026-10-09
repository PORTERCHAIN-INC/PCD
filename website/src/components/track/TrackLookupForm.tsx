"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";
import { ArrowRight } from "lucide-react";
import { useRouter } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

/** One input, one button. Used as the /track hero and under a tracking result. */
export default function TrackLookupForm({
  initial = "",
  size = "lg",
}: {
  initial?: string;
  size?: "lg" | "md";
}) {
  const t = useTranslations("portal.customer");
  const router = useRouter();
  const id = useId();
  const [value, setValue] = useState(initial);
  const [pending, setPending] = useState(false);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const v = value.trim().toUpperCase();
    if (!v) return;
    setPending(true);
    router.push(`/track/${encodeURIComponent(v)}`);
  }

  return (
    <form onSubmit={submit} className="w-full" data-testid="track-form" suppressHydrationWarning>
      <label htmlFor={id} className="sr-only">
        {t("guestTrackPlaceholder")}
      </label>
      <div
        className={cn(
          "flex w-full items-center gap-2 rounded-2xl border border-primary/15 bg-white p-1.5 shadow-sm focus-within:border-secondary focus-within:ring-4 focus-within:ring-secondary/15",
          size === "lg" && "sm:p-2"
        )}
      >
        <input
          id={id}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={t("guestTrackPlaceholder")}
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          inputMode="text"
          required
          className={cn(
            "min-w-0 flex-1 bg-transparent px-3 font-mono tracking-wide text-primary outline-none placeholder:text-muted/70",
            size === "lg" ? "h-12 text-lg sm:h-14 sm:text-xl" : "h-11 text-base"
          )}
        />
        <button
          type="submit"
          disabled={pending}
          className={cn(
            "inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-primary px-5 font-semibold text-white transition-colors hover:bg-[#152238] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2 disabled:opacity-70",
            size === "lg" ? "h-12 text-base sm:h-14 sm:px-7" : "h-11 text-sm"
          )}
        >
          {t("guestTrackSubmit")}
          <ArrowRight className="h-4 w-4" aria-hidden />
        </button>
      </div>
    </form>
  );
}
