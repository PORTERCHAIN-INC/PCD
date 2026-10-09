import { getTranslations } from "next-intl/server";
import Container from "@/components/ui/Container";
import CoreFaqList from "@/components/marketing/faq/CoreFaqList";

/** Homepage FAQ — the first six of the one buyer FAQ (data/faq-core) + FAQPage JSON-LD. */
export default async function HomeFaq({ locale }: { locale: string }) {
  const t = await getTranslations({ locale, namespace: "faq" });
  return (
    <section className="bg-gray-bg" aria-labelledby="home-faq-heading">
      <Container size="narrow" className="py-16 sm:py-24">
        <h2
          id="home-faq-heading"
          className="text-3xl font-semibold tracking-tight text-primary sm:text-4xl"
        >
          {t("title")}
        </h2>
        <p className="mt-2 text-base text-muted">{t("subtitle")}</p>
        <div className="mt-8">
          <CoreFaqList locale={locale} limit={6} />
        </div>
      </Container>
    </section>
  );
}
