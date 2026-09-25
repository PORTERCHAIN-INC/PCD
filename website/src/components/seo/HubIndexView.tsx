import { Link } from "@/i18n/navigation";
import { getTranslations } from "next-intl/server";
import Container from "@/components/ui/Container";
import MarketingHero from "@/components/marketing/MarketingHero";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { getPageHeroImage } from "@/data/site-images";
import MarketingCloser from "@/components/marketing/MarketingCloser";
import type { Locale } from "@/i18n/routing";
import { quoteContact, contact } from "@/lib/seo/routes";

interface HubIndexViewProps {
  locale: Locale;
  title: string;
  description: string;
  items: { href: string; title: string; description: string }[];
  ctaSource: string;
  /** Set false when breadcrumbs already clear the fixed navbar. */
  clearNav?: boolean;
}

export default async function HubIndexView({
  locale,
  title,
  description,
  items,
  ctaSource,
  clearNav = true,
}: HubIndexViewProps) {
  const tCta = await getTranslations("common.cta");
  const quoteLabel = tCta("quote");

  return (
    <>
      <MarketingHero
        badge="Resources"
        title={title}
        subtitle={description}
        primaryCta={quoteLabel}
        primaryHref={quoteContact(locale, ctaSource)}
        secondaryCta="Contact"
        secondaryHref={contact(locale, { from: ctaSource })}
        variant="light-centered"
        clearNav={clearNav}
        illustration={<HeroPhoto image={getPageHeroImage(ctaSource)} />}
      />
      <section className="site-section bg-white">
        <Container>
          <div className="grid md:grid-cols-2 gap-6">
            {items.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="block rounded-2xl border border-primary/10 p-6 hover:border-secondary/40 hover:shadow-sm transition-all"
              >
                <h2 className="text-lg font-semibold text-primary">{item.title}</h2>
                <p className="mt-2 text-sm text-muted leading-relaxed">{item.description}</p>
              </Link>
            ))}
          </div>
        </Container>
      </section>
      <MarketingCloser
        title="Need help choosing the right dispatch setup?"
        primaryLabel={quoteLabel}
        primaryHref={quoteContact(locale, ctaSource)}
        secondaryLabel="Contact us"
        secondaryHref={contact(locale, { from: ctaSource })}
        variant="dark"
      />
    </>
  );
}
