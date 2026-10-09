import { getTranslations } from "next-intl/server";
import { Calculator, Clock3, Headset, MapPinned } from "lucide-react";
import { COVERAGE_FSA_COUNT } from "@/lib/seo/delivery-programmatic";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/marketing/ui/SectionHeader";

/**
 * "Why PorterChain" — a need → what-you-get comparison. Every row is a shipped capability or a
 * published fact (instant price API, delivery promise, tracking + POD, office hours); no claims
 * about competitors and no invented numbers.
 */
const ROWS = [
  { id: "price", Icon: Calculator },
  { id: "speed", Icon: Clock3 },
  { id: "tracking", Icon: MapPinned },
  { id: "team", Icon: Headset },
] as const;

export default async function HomeWhy({ locale, promise }: { locale: string; promise: string }) {
  const t = await getTranslations({ locale, namespace: "homePage.why" });
  return (
    <section className="bg-gray-bg" aria-labelledby="home-why-heading">
      <Container className="grid gap-10 py-16 sm:py-24 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:gap-16">
        <SectionHeader
          id="home-why-heading"
          eyebrow={t("eyebrow")}
          title={t("title")}
          lead={t("lead", { count: COVERAGE_FSA_COUNT })}
        />
        <div className="overflow-hidden rounded-3xl border border-primary/8 bg-white shadow-xl shadow-primary/5">
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">{t("caption")}</caption>
            <thead className="bg-gray-bg">
              <tr>
                <th
                  scope="col"
                  className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-muted sm:px-6"
                >
                  {t("colNeed")}
                </th>
                <th
                  scope="col"
                  className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-muted sm:px-6"
                >
                  {t("colGet")}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-primary/8">
              {ROWS.map(({ id, Icon }) => (
                <tr key={id} className="align-top">
                  <th scope="row" className="px-5 py-5 sm:px-6">
                    <span className="flex items-center gap-3">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-secondary/10 text-secondary">
                        <Icon className="h-4.5 w-4.5" aria-hidden />
                      </span>
                      <span className="text-sm font-semibold text-primary sm:text-base">
                        {t(`rows.${id}.need`)}
                      </span>
                    </span>
                  </th>
                  <td className="px-5 py-5 text-sm leading-relaxed text-primary/85 sm:px-6 sm:text-base">
                    <span className="font-semibold text-primary">{t(`rows.${id}.title`)}</span>{" "}
                    {id === "speed" ? promise : t(`rows.${id}.body`)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Container>
    </section>
  );
}
