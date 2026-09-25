import { Link } from "@/i18n/navigation";
import { getTranslations } from "next-intl/server";
import Container from "@/components/ui/Container";
import CtaSection from "@/components/corporate/sections/CtaSection";
import type { Locale } from "@/i18n/routing";
import { contact } from "@/lib/seo/routes";

type DocsHubItem = {
  href: string;
  title: string;
  description: string;
  external?: boolean;
};

interface DeveloperDocsHubBodyProps {
  locale: Locale;
  title: string;
  subtitle: string;
  items: DocsHubItem[];
}

export default async function DeveloperDocsHubBody({
  locale,
  title,
  subtitle,
  items,
}: DeveloperDocsHubBodyProps) {
  const tCta = await getTranslations("common.cta");
  const quoteLabel = tCta("quote");

  return (
    <>
      <section className="site-section bg-gray-bg">
        <Container>
          <h2 className="text-2xl font-semibold text-primary">{title}</h2>
          <p className="mt-2 max-w-2xl text-muted leading-relaxed">{subtitle}</p>
          <div className="mt-8 grid md:grid-cols-2 gap-6">
            {items.map((item) => {
              const card = (
                <>
                  <h3 className="text-lg font-semibold text-primary">{item.title}</h3>
                  <p className="mt-2 text-sm text-muted leading-relaxed">{item.description}</p>
                </>
              );
              const className =
                "block rounded-2xl border border-primary/10 bg-white p-6 hover:border-secondary/40 hover:shadow-sm transition-all";

              if (item.external) {
                return (
                  <a
                    key={item.href}
                    href={item.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={className}
                  >
                    {card}
                  </a>
                );
              }

              return (
                <Link key={item.href} href={item.href} className={className}>
                  {card}
                </Link>
              );
            })}
          </div>
        </Container>
      </section>
      <CtaSection
        title="Need integration support?"
        subtitle="Our partner engineering team helps with ERP, WMS, and webhook rollouts."
        primaryLabel={quoteLabel}
        primaryHref={contact(locale, { from: "developers-docs" })}
        secondaryLabel="Back to developers"
        secondaryHref="/developers"
        variant="gradient"
      />
    </>
  );
}
