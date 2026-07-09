import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import HeroSection from "@/components/corporate/sections/HeroSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { getPageHeroImage } from "@/data/site-images";
import CtaSection from "@/components/corporate/sections/CtaSection";
import type { Locale } from "@/i18n/routing";
import { demoContact, contact } from "@/lib/seo/routes";

interface HubIndexViewProps {
  locale: Locale;
  title: string;
  description: string;
  items: { href: string; title: string; description: string }[];
  ctaSource: string;
}

export default function HubIndexView({
  locale,
  title,
  description,
  items,
  ctaSource,
}: HubIndexViewProps) {
  return (
    <>
      <HeroSection
        badge="Resources"
        title={title}
        subtitle={description}
        primaryCta="Get a quote"
        primaryHref={demoContact(locale, ctaSource)}
        secondaryCta="Contact"
        secondaryHref={contact(locale, { from: ctaSource })}
        variant="light-centered"
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
      <CtaSection
        title="Need help choosing the right dispatch setup?"
        primaryLabel="Get a quote"
        primaryHref={demoContact(locale, ctaSource)}
        secondaryLabel="Contact us"
        secondaryHref={contact(locale, { from: ctaSource })}
        variant="dark"
      />
    </>
  );
}
