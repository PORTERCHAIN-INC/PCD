"use client";

import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import InquiryForm from "@/components/business/InquiryForm";
import BlurFade from "@/components/magic/blur-fade";

export default function FinalCta() {
  const t = useTranslations("businessPage.finalCta");

  return (
    <section className="relative biz-section bg-[#091b1c] overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_0%,rgba(255,122,0,0.12)_0%,transparent_60%)]" />
      <Container className="relative">
        <BlurFade inView className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="biz-heading lg:text-5xl text-white tracking-tight">{t("title")}</h2>
          <p className="mt-5 text-lg text-white/60 leading-relaxed">{t("subtitle")}</p>
        </BlurFade>

        <BlurFade delay={0.1} inView>
          <div className="mx-auto max-w-xl">
            <InquiryForm id="inquiry-final" variant="final" />
          </div>
        </BlurFade>
      </Container>
    </section>
  );
}
