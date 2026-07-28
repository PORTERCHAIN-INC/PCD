import { getTranslations } from "next-intl/server";
import Container from "@/components/ui/Container";
import AnswerBlock from "@/components/seo/AnswerBlock";
import FadeIn from "@/components/corporate/motion/FadeIn";
import LinkButton from "@/components/corporate/ui/LinkButton";

type Props = { locale: string };

export default async function HomeAnswerSection({ locale }: Props) {
  const t = await getTranslations({ locale, namespace: "corporate.home.answers" });

  const items = [
    { question: t("what.question"), answer: t("what.answer") },
    { question: t("who.question"), answer: t("who.answer") },
    { question: t("where.question"), answer: t("where.answer") },
    { question: t("how.question"), answer: t("how.answer") },
  ];

  return (
    <section
      className="relative overflow-hidden border-y border-primary/6 bg-gray-bg"
      aria-labelledby="home-answers-heading"
    >
      <div className="pointer-events-none absolute inset-0 grid-pattern opacity-30" aria-hidden />
      <Container className="relative py-10 sm:py-12 lg:py-14">
        <FadeIn>
          <p className="type-caption mb-3 font-bold text-secondary">{t("eyebrow")}</p>
          <AnswerBlock
            title={t("title")}
            titleId="home-answers-heading"
            items={items}
            tone="light"
            layout="grid"
          />
        </FadeIn>

        <FadeIn delay={0.12} className="mt-10 flex flex-wrap items-center gap-3 sm:mt-12">
          <LinkButton
            href="/contact?intent=quote&from=home-answers"
            trackLabel={t("cta")}
            trackSource="home_answers"
          >
            {t("cta")}
          </LinkButton>
          <LinkButton
            href="/business#fleet"
            variant="outline"
            trackLabel={t("secondaryCta")}
            trackSource="home_answers"
          >
            {t("secondaryCta")}
          </LinkButton>
        </FadeIn>
      </Container>
    </section>
  );
}
