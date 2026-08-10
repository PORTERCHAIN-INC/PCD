"use client";

import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import QuoteSignupPanel from "@/components/business/QuoteSignupPanel";
import BlurFade from "@/components/magic/blur-fade";

export default function FinalCta() {
  const t = useTranslations("businessPage.finalCta");

  return (
    <section className="relative biz-section overflow-hidden bg-[#0b1220]">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_0%,rgba(37,99,235,0.18)_0%,transparent_60%)]" />
      <Container className="relative">
        <BlurFade inView className="mx-auto mb-12 max-w-2xl text-center">
          <h2 className="biz-heading tracking-tight text-white lg:text-5xl">{t("title")}</h2>
          <p className="mt-5 text-lg leading-relaxed text-white/60">{t("subtitle")}</p>
        </BlurFade>

        <BlurFade delay={0.1} inView>
          <div className="mx-auto max-w-xl">
            <QuoteSignupPanel id="inquiry-final" variant="final" from="business-final" />
          </div>
        </BlurFade>
      </Container>
    </section>
  );
}
