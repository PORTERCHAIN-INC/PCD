import { getTranslations } from "next-intl/server";
import { CalendarCheck, Calculator, MapPinned } from "lucide-react";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/marketing/ui/SectionHeader";

const STEPS = [
  { id: "price", Icon: Calculator },
  { id: "book", Icon: CalendarCheck },
  { id: "track", Icon: MapPinned },
] as const;

export default async function HomeHowItWorks({ locale }: { locale: string }) {
  const t = await getTranslations({ locale, namespace: "homePage.howItWorks" });
  return (
    <section className="bg-white" aria-labelledby="home-how-heading">
      <Container className="py-16 sm:py-24">
        <div className="flex items-end justify-between gap-6">
          <SectionHeader id="home-how-heading" eyebrow={t("eyebrow")} title={t("title")} />
        </div>
        <ol className="relative mt-10 grid gap-4 md:grid-cols-3 md:gap-6">
          <span
            className="absolute left-[16.5%] right-[16.5%] top-[2.375rem] hidden h-0.5 bg-secondary/50 md:block draw-on-view"
            aria-hidden
          />
          {STEPS.map(({ id, Icon }, index) => (
            <li
              key={id}
              className="relative rounded-2xl border border-primary/8 bg-gray-bg p-6 md:bg-transparent md:border-transparent md:p-0 md:text-center"
            >
              <div className="flex items-center gap-3 md:flex-col md:gap-0">
                <span className="relative flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-white shadow-lg shadow-primary/20 md:mx-auto md:h-[4.75rem] md:w-[4.75rem] md:rounded-3xl">
                  <Icon className="h-5 w-5 md:h-7 md:w-7" aria-hidden />
                  <span className="absolute -right-1.5 -top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-secondary text-xs font-bold text-white ring-2 ring-white">
                    {index + 1}
                  </span>
                </span>
                <h3 className="text-lg font-semibold text-primary md:mt-5">
                  {t(`steps.${id}.title`)}
                </h3>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-muted md:mx-auto md:max-w-xs md:text-base">
                {t(`steps.${id}.body`)}
              </p>
            </li>
          ))}
        </ol>
      </Container>
    </section>
  );
}
