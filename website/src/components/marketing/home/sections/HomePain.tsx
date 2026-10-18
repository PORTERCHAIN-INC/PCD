import { getTranslations } from "next-intl/server";
import { ArrowRight, X } from "lucide-react";
import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import { HOME_PRICE_ANCHOR_ID } from "@/lib/marketing/price-bar";

/**
 * Problem → agitation → solution band. The four pains are the friction a business feels with a
 * typical courier (no names, no numbers); the promise line only states shipped capabilities.
 */
const PAINS = ["quote", "window", "where", "fit"] as const;

export default async function HomePain({ locale }: { locale: string }) {
  const t = await getTranslations({ locale, namespace: "homePage.pain" });
  return (
    <section className="bg-white" aria-labelledby="home-pain-heading">
      <Container className="grid gap-8 py-14 sm:py-20 lg:grid-cols-2 lg:items-center lg:gap-16">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-secondary sm:text-sm">
            {t("eyebrow")}
          </p>
          <h2
            id="home-pain-heading"
            className="mt-3 text-balance text-3xl font-semibold tracking-tight text-primary sm:text-4xl"
          >
            {t("title")}
          </h2>
          <ul className="mt-6 space-y-3">
            {PAINS.map((id) => (
              <li key={id} className="flex items-start gap-3 text-base text-primary/85">
                <X className="mt-1 h-4 w-4 shrink-0 text-red-600" aria-hidden />
                {t(`items.${id}`)}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-3xl border border-primary/8 bg-gray-bg p-6 sm:p-8">
          <p className="text-lg leading-relaxed text-primary">{t("promise")}</p>
          <Link
            href={`#${HOME_PRICE_ANCHOR_ID}`}
            className="mt-6 inline-flex min-h-[var(--touch-min)] items-center gap-2 rounded-full bg-secondary px-5 text-sm font-semibold text-white transition-colors hover:bg-secondary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2"
          >
            {t("cta")}
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        </div>
      </Container>
    </section>
  );
}
