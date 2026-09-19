import { getTranslations } from "next-intl/server";
import Container from "@/components/ui/Container";
import HubMapStage from "@/components/hub/HubMapStage";
import HubOfferCards from "@/components/hub/HubOfferCards";
import HubStatusChip from "@/components/hub/HubStatusChip";
import HubTimeline from "@/components/hub/HubTimeline";

/** Advanced-UI facade panels above existing business sections (illustrative). */
export default async function BusinessHubFacade({ locale }: { locale: string }) {
  const t = await getTranslations({ locale, namespace: "businessPage.hubFacade" });

  const offers = [
    {
      id: "same-day",
      title: t("offers.sameDay.title"),
      badge: t("offers.sameDay.badge"),
      meta: t("offers.sameDay.meta"),
      ctaLabel: t("offers.sameDay.cta"),
    },
    {
      id: "recurring",
      title: t("offers.recurring.title"),
      badge: t("offers.recurring.badge"),
      meta: t("offers.recurring.meta"),
      ctaLabel: t("offers.recurring.cta"),
    },
    {
      id: "overflow",
      title: t("offers.overflow.title"),
      badge: t("offers.overflow.badge"),
      meta: t("offers.overflow.meta"),
      ctaLabel: t("offers.overflow.cta"),
    },
  ];

  const steps = [
    { id: "request", label: t("timeline.request.label"), detail: t("timeline.request.detail") },
    { id: "match", label: t("timeline.match.label"), detail: t("timeline.match.detail") },
    { id: "deliver", label: t("timeline.deliver.label"), detail: t("timeline.deliver.detail") },
  ];

  return (
    <section
      className="border-b border-primary/6 bg-[#F4F6FA]"
      aria-labelledby="business-hub-facade"
    >
      <Container className="py-10 sm:py-12">
        <div className="mb-6 flex flex-wrap items-center gap-2">
          <h2 id="business-hub-facade" className="text-lg font-semibold text-primary sm:text-xl">
            {t("title")}
          </h2>
          <HubStatusChip label={t("chip")} tone="info" />
        </div>
        <div className="grid gap-6 lg:grid-cols-12">
          <div className="lg:col-span-4">
            <HubOfferCards items={offers} illustrativeNote={t("illustrativeNote")} />
          </div>
          <div className="lg:col-span-5">
            <HubMapStage title={t("mapTitle")} subtitle={t("mapSubtitle")} />
          </div>
          <div className="rounded-2xl border border-primary/8 bg-white p-5 shadow-sm lg:col-span-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-secondary">
              {t("timelineTitle")}
            </p>
            <div className="mt-4">
              <HubTimeline steps={steps} />
            </div>
          </div>
        </div>
      </Container>
    </section>
  );
}
