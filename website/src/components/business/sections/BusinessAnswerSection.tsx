import { getTranslations } from "next-intl/server";
import Container from "@/components/ui/Container";
import AnswerBlock from "@/components/seo/AnswerBlock";
import FadeIn from "@/components/corporate/motion/FadeIn";
import LinkButton from "@/components/corporate/ui/LinkButton";
import { HUB_FROM } from "@/lib/marketing/config";

/** AEO AnswerBlock on Merchants hub (/business). */
export default async function BusinessAnswerSection({ locale }: { locale: string }) {
  const t = await getTranslations({ locale, namespace: "businessPage.answers" });

  const items = [
    { question: t("what.question"), answer: t("what.answer") },
    { question: t("who.question"), answer: t("who.answer") },
    { question: t("where.question"), answer: t("where.answer") },
    { question: t("how.question"), answer: t("how.answer") },
  ];

  return (
    <section
      className="relative overflow-hidden border-y border-primary/6 bg-white"
      aria-labelledby="business-answers-heading"
    >
      <Container className="relative py-10 sm:py-12">
        <FadeIn>
          <p className="type-caption mb-3 font-bold text-secondary">{t("eyebrow")}</p>
          <AnswerBlock
            title={t("title")}
            titleId="business-answers-heading"
            items={items}
            tone="light"
            layout="grid"
          />
        </FadeIn>
        <FadeIn delay={0.1} className="mt-8">
          <LinkButton
            href={`/contact?intent=quote&from=${HUB_FROM.merchants}`}
            trackLabel={t("cta")}
            className="btn-primary"
          >
            {t("cta")}
          </LinkButton>
        </FadeIn>
      </Container>
    </section>
  );
}
