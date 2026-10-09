import { getTranslations } from "next-intl/server";
import { ChevronDown } from "lucide-react";
import Container from "@/components/ui/Container";
import { JsonLd } from "@/components/seo";
import { buildFAQPageSchema } from "@/lib/seo/schema";

type FaqItem = { question: string; answer: string };

/** Homepage FAQ — the guarded B2B playbook set (`faq.items`) + FAQPage JSON-LD. No JS: <details>. */
export default async function HomeFaq({ locale }: { locale: string }) {
  const t = await getTranslations({ locale, namespace: "faq" });
  const items = (t.raw("items") as FaqItem[]).filter((i) => i.question && i.answer);
  if (!items.length) return null;
  return (
    <section className="bg-gray-bg" aria-labelledby="home-faq-heading">
      <JsonLd data={buildFAQPageSchema(items)} />
      <Container size="narrow" className="py-16 sm:py-24">
        <h2
          id="home-faq-heading"
          className="text-3xl font-semibold tracking-tight text-primary sm:text-4xl"
        >
          {t("title")}
        </h2>
        <p className="mt-2 text-base text-muted">{t("subtitle")}</p>
        <div className="mt-8 divide-y divide-primary/10 border-y border-primary/10">
          {items.map((item) => (
            <details key={item.question} className="group">
              <summary className="flex min-h-[3.25rem] cursor-pointer list-none items-center justify-between gap-4 py-4 text-left text-base font-semibold text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary rounded [&::-webkit-details-marker]:hidden">
                {item.question}
                <ChevronDown
                  className="h-5 w-5 shrink-0 text-muted transition-transform group-open:rotate-180 motion-reduce:transition-none"
                  aria-hidden
                />
              </summary>
              <p className="pb-5 pr-8 text-base leading-relaxed text-muted">{item.answer}</p>
            </details>
          ))}
        </div>
      </Container>
    </section>
  );
}
