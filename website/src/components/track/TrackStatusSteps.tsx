"use client";

import { useTranslations } from "next-intl";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { TRACK_STEPS, trackStatus } from "@/lib/track-status";

/** Five-step status rail. Current step is announced; colour is never the only signal. */
export default function TrackStatusSteps({
  state,
  delivered,
}: {
  state: string | null | undefined;
  delivered: boolean;
}) {
  const t = useTranslations("booking.track");
  const status = trackStatus(state, delivered);

  if (status.kind === "exception") {
    return (
      <div
        className="rounded-2xl border border-amber-300 bg-amber-50 p-5"
        role="status"
        data-testid="track-status"
        data-status="exception"
      >
        <p className="text-sm font-semibold text-amber-900">{t("exceptionTitle")}</p>
        <p className="mt-1 text-sm text-amber-900">{t("exceptionBody")}</p>
      </div>
    );
  }

  const current = status.step;
  const done = current === TRACK_STEPS.length - 1;
  return (
    <div data-testid="track-status" data-status={TRACK_STEPS[current]}>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{t("status")}</p>
      <p
        className={cn(
          "mt-1 text-3xl font-bold tracking-tight",
          done ? "text-success" : "text-primary"
        )}
        role="status"
      >
        {t(`steps.${TRACK_STEPS[current]}`)}
      </p>
      <ol className="mt-6 grid grid-cols-5 gap-1.5" aria-label={t("progressLabel")}>
        {TRACK_STEPS.map((step, i) => (
          <li key={step} className="min-w-0">
            <span
              className={cn(
                "block h-1.5 rounded-full",
                i < current || done
                  ? "bg-success"
                  : i === current
                    ? "bg-secondary"
                    : "bg-primary/10"
              )}
              aria-hidden
            />
            <span
              className={cn(
                "mt-2 flex items-center gap-1 text-[11px] leading-tight sm:text-xs",
                i <= current ? "font-semibold text-primary" : "text-muted"
              )}
            >
              {i < current || (done && i === current) ? (
                <Check className="hidden h-3 w-3 shrink-0 text-success sm:block" aria-hidden />
              ) : null}
              <span className="truncate">{t(`steps.${step}`)}</span>
              <span className="sr-only">
                {i < current
                  ? ` — ${t("stepDone")}`
                  : i === current
                    ? ` — ${t("stepCurrent")}`
                    : ""}
              </span>
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
