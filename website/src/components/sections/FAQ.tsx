"use client";

import { useTranslations } from "next-intl";
import SectionHeader from "@/components/ui/SectionHeader";
import Accordion from "@/components/ui/Accordion";
import Container from "@/components/ui/Container";

export default function FAQ() {
  const t = useTranslations("faq");
  const items = t.raw("items") as { question: string; answer: string }[];

  return (
    <section id="about" className="site-section bg-white">
      <Container size="narrow">
        <SectionHeader label={t("label")} title={t("title")} subtitle={t("subtitle")} />
        <Accordion items={items} />
      </Container>
    </section>
  );
}
