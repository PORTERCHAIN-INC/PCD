"use client";

import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import ShimmerButton from "@/components/magic/shimmer-button";
import BlurFade from "@/components/magic/blur-fade";

export default function StoryCta() {
  const t = useTranslations("corporate.home.story.cta");

  return (
    <section className="relative overflow-hidden bg-primary py-20 sm:py-24">
      <div className="absolute inset-0 pointer-events-none" aria-hidden>
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_0%,rgba(37,99,235,0.25)_0%,transparent_55%)]" />
        <div className="absolute inset-0 dot-pattern opacity-20" />
      </div>
      <Container className="relative">
        <BlurFade inView className="max-w-2xl mx-auto text-center">
          <h2 className="pc-display text-white text-balance">{t("title")}</h2>
          <p className="mt-4 text-lg text-white/65 leading-relaxed">{t("subtitle")}</p>
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
            <ShimmerButton
              href="/sign-up?intent=quote&from=home-final"
              variant="onDark"
              showArrow
              trackSource="home-final"
            >
              {t("primary")}
            </ShimmerButton>
          </div>
        </BlurFade>
      </Container>
    </section>
  );
}
