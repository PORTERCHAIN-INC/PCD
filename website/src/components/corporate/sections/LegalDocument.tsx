"use client";

import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import FadeIn from "@/components/corporate/motion/FadeIn";

export type LegalPageId = "privacy" | "terms" | "cookies";

interface LegalSection {
  title: string;
  paragraphs: string[];
  list?: string[];
}

interface LegalDocumentProps {
  pageId: LegalPageId;
}

export default function LegalDocument({ pageId }: LegalDocumentProps) {
  const t = useTranslations(`legal.${pageId}`);
  const sections = t.raw("sections") as LegalSection[];

  return (
    <article className="site-section bg-white pt-28 md:pt-32 pb-16 md:pb-20">
      <Container className="max-w-3xl">
        <FadeIn>
          <p className="text-xs font-semibold uppercase tracking-wider text-secondary mb-3">
            {t("updated")}
          </p>
          <h1 className="text-3xl md:text-4xl font-bold text-primary tracking-tight">
            {t("title")}
          </h1>
          <p className="mt-6 text-base text-muted leading-relaxed">{t("intro")}</p>
        </FadeIn>

        <div className="mt-12 space-y-10">
          {sections.map((section, i) => (
            <FadeIn key={section.title} delay={i * 0.04}>
              <section>
                <h2 className="text-xl font-semibold text-primary tracking-tight">
                  {section.title}
                </h2>
                <div className="mt-4 space-y-4">
                  {section.paragraphs.map((paragraph) => (
                    <p key={paragraph.slice(0, 48)} className="text-sm text-muted leading-relaxed">
                      {paragraph}
                    </p>
                  ))}
                  {section.list && (
                    <ul className="list-disc pl-5 space-y-2">
                      {section.list.map((item) => (
                        <li key={item.slice(0, 48)} className="text-sm text-muted leading-relaxed">
                          {item}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </section>
            </FadeIn>
          ))}
        </div>
      </Container>
    </article>
  );
}
