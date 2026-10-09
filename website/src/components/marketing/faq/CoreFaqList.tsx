import { ArrowRight, ChevronDown } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { JsonLd } from "@/components/seo";
import { buildFAQPageSchema } from "@/lib/seo/schema";
import { CORE_FAQ_GROUPS, coreFaq, type CoreFaqGroup } from "@/data/faq-core";
import FaqFilter from "@/components/marketing/faq/FaqFilter";

/** Server-rendered <details> list (no JS needed to read); optional grouping + light filter. */
export default function CoreFaqList({
  locale,
  limit,
  grouped = false,
  filter = false,
  schema = true,
}: {
  locale: string;
  limit?: number;
  grouped?: boolean;
  filter?: boolean;
  schema?: boolean;
}) {
  const items = coreFaq(locale).slice(0, limit);
  const groups = grouped
    ? (Object.keys(CORE_FAQ_GROUPS.en) as CoreFaqGroup[]).map((g) => ({
        id: g,
        title: CORE_FAQ_GROUPS[locale === "fr" ? "fr" : "en"][g],
        items: items.filter((i) => i.group === g),
      }))
    : [{ id: "all", title: "", items }];

  return (
    <div id="core-faq" data-testid="core-faq">
      {schema ? (
        <JsonLd
          data={buildFAQPageSchema(items.map((i) => ({ question: i.question, answer: i.answer })))}
        />
      ) : null}
      {filter ? <FaqFilter targetId="core-faq" locale={locale} /> : null}
      {groups.map((g) => (
        <div key={g.id} data-faq-group className={g.title ? "mt-8 first-of-type:mt-0" : undefined}>
          {g.title ? (
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted">{g.title}</h2>
          ) : null}
          <div className="mt-2 divide-y divide-primary/10 border-y border-primary/10">
            {g.items.map((item) => (
              <details
                key={item.id}
                id={`faq-${item.id}`}
                className="group"
                data-faq-item
                data-faq-text={`${item.question} ${item.answer}`.toLowerCase()}
              >
                <summary className="flex min-h-[3.25rem] cursor-pointer list-none items-center justify-between gap-4 rounded py-4 text-left text-base font-semibold text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary [&::-webkit-details-marker]:hidden">
                  {item.question}
                  <ChevronDown
                    className="h-5 w-5 shrink-0 text-muted transition-transform group-open:rotate-180 motion-reduce:transition-none"
                    aria-hidden
                  />
                </summary>
                <div className="pb-5 pr-8">
                  <p className="text-base leading-relaxed text-muted">{item.answer}</p>
                  <Link
                    href={item.link.href}
                    className="mt-2 inline-flex min-h-8 items-center gap-1 text-sm font-semibold text-secondary underline-offset-4 hover:underline"
                  >
                    {item.link.label}
                    <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                  </Link>
                </div>
              </details>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
