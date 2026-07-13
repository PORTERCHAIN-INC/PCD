"use client";

import { useTranslations } from "next-intl";
import SectionHeader from "@/components/ui/SectionHeader";
import Container from "@/components/ui/Container";

export default function Testimonials() {
  const t = useTranslations("testimonials");

  return (
    <section className="site-section bg-gray-bg">
      <Container>
        <SectionHeader label={t("label")} title={t("title")} subtitle={t("subtitle")} />
        <p className="mx-auto max-w-2xl text-center text-muted type-body leading-relaxed">
          {t("placeholder")}
        </p>
      </Container>
    </section>
  );
}
