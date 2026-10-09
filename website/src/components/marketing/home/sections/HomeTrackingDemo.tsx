import { getTranslations } from "next-intl/server";
import { ArrowRight, Check } from "lucide-react";
import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import { cn } from "@/lib/utils";
import SectionHeader from "@/components/marketing/ui/SectionHeader";
import LottieMotion from "@/components/motion/LottieMotion";

const STEPS = ["booked", "assigned", "pickedUp", "outForDelivery", "delivered"] as const;
/** Index of the step currently in progress in the static sample. */
const CURRENT = 3;

/**
 * Live-tracking demo — a STATIC, clearly labelled sample (badge + note). It does not call the
 * tracking API and shows no real order, driver or customer data.
 */
export default async function HomeTrackingDemo({ locale }: { locale: string }) {
  const t = await getTranslations({ locale, namespace: "homePage.trackingDemo" });
  return (
    <section className="bg-white" aria-labelledby="home-tracking-heading">
      <Container className="grid items-center gap-10 py-16 sm:py-24 lg:grid-cols-2 lg:gap-16">
        <div className="max-w-xl">
          <SectionHeader
            id="home-tracking-heading"
            eyebrow={t("eyebrow")}
            title={t("title")}
            lead={t("body")}
          />
          <Link
            href="/track"
            className="mt-6 inline-flex min-h-[var(--touch-min)] items-center gap-2 rounded-full border border-primary/15 bg-white px-6 py-3 text-sm font-semibold text-primary hover:border-secondary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2"
          >
            {t("cta")}
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        </div>

        <figure
          className="rounded-3xl border border-primary/8 bg-white p-6 shadow-2xl shadow-primary/10 sm:p-8"
          data-testid="tracking-sample"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-primary">{t("order")}</p>
              <p className="mt-0.5 text-sm text-muted">{t("route")}</p>
            </div>
            <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-amber-900">
              {t("sampleBadge")}
            </span>
          </div>
          <LottieMotion
            src="/lottie/van-route.json"
            aspect={3}
            stillFrame={100}
            className="mt-4 rounded-2xl bg-gray-bg"
            testId="tracking-motion"
          />
          <p className="mt-3 text-2xl font-semibold tracking-tight text-primary">{t("eta")}</p>
          <ol className="mt-5 space-y-0">
            {STEPS.map((step, index) => {
              const done = index < CURRENT;
              const current = index === CURRENT;
              return (
                <li key={step} className="relative flex gap-3 pb-5 last:pb-0">
                  {index < STEPS.length - 1 ? (
                    <span
                      className={cn(
                        "absolute left-[0.6875rem] top-6 h-[calc(100%-1.25rem)] w-0.5",
                        done ? "bg-secondary" : "bg-primary/10"
                      )}
                      aria-hidden
                    />
                  ) : null}
                  <span
                    className={cn(
                      "relative flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
                      done && "bg-secondary text-white",
                      current && "bg-white ring-2 ring-secondary",
                      !done && !current && "bg-white ring-2 ring-primary/15"
                    )}
                    aria-hidden
                  >
                    {done ? <Check className="h-3.5 w-3.5" /> : null}
                    {current ? <span className="h-2 w-2 rounded-full bg-secondary" /> : null}
                  </span>
                  <div className="flex min-w-0 flex-1 items-baseline justify-between gap-3">
                    <span
                      className={cn(
                        "text-sm",
                        done || current ? "font-semibold text-primary" : "text-muted"
                      )}
                    >
                      {t(`steps.${step}`)}
                    </span>
                    <span className="shrink-0 text-xs tabular-nums text-muted">
                      {t(`times.${step}`)}
                    </span>
                  </div>
                </li>
              );
            })}
          </ol>
          <figcaption className="mt-5 border-t border-primary/8 pt-3 text-xs text-muted">
            {t("sampleNote")}
          </figcaption>
        </figure>
      </Container>
    </section>
  );
}
