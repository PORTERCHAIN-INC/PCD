import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import ContactHero from "@/components/corporate/sections/ContactHero";
import ContactInfoPanel from "@/components/corporate/sections/ContactInfoPanel";
import ContactInquiryForm from "@/components/corporate/sections/ContactInquiryForm";
import ContactDepartmentCards from "@/components/corporate/sections/ContactDepartmentCards";
import ContactSocialBar from "@/components/corporate/sections/ContactSocialBar";
import GoogleBusinessProfileLink from "@/components/integrations/GoogleBusinessProfileLink";
import FaqSection from "@/components/corporate/sections/FaqSection";
import Container from "@/components/ui/Container";
import FadeIn from "@/components/corporate/motion/FadeIn";
import { collectFaqItems } from "@/lib/corporate-content";
import { TrendingUp, Headphones, Building2, Truck, Code2 } from "lucide-react";
import { JsonLd } from "@/components/seo";
import { buildLocalBusinessSchema } from "@/lib/seo/schema";
import SlaResponseCountdown from "@/components/seo/SlaResponseCountdown";

type Props = {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ intent?: string; from?: string }>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.contact" });
  return buildPageMetadata(locale, "contact", t("title"), t("description"));
}

const DEPT_ICONS = [TrendingUp, Headphones, Building2, Truck, Code2];

export default async function ContactPage({ params, searchParams }: Props) {
  const { locale } = await params;
  const { intent, from } = await searchParams;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.contact");
  const tInfo = await getTranslations("corporate.contact.info");

  const contactInfo = {
    phoneLabel: tInfo("phoneLabel"),
    phone: tInfo("phone"),
    phoneHref: tInfo("phoneHref"),
    emailLabel: tInfo("emailLabel"),
    email: tInfo("email"),
    emailHref: tInfo("emailHref"),
    whatsappLabel: tInfo("whatsappLabel"),
    whatsapp: tInfo("whatsapp"),
    whatsappHref: tInfo("whatsappHref"),
    hoursLabel: tInfo("hoursLabel"),
    hours: tInfo("hours"),
    emergencyLabel: tInfo("emergencyLabel"),
    emergency: tInfo("emergency"),
    emergencyDetail: tInfo("emergencyDetail"),
  };

  const isQuote = intent === "quote";
  const heroTitle = isQuote ? t("heroQuote.title") : t("hero.title");
  const heroSubtitle = isQuote ? t("heroQuote.subtitle") : t("hero.subtitle");

  const departmentCards = DEPT_ICONS.map((icon, i) => ({
    title: t(`departments.items.${i}.title`),
    description: t(`departments.items.${i}.description`),
    contact: t(`departments.items.${i}.contact`),
    href: `mailto:${t(`departments.items.${i}.contact`)}`,
    icon,
  }));

  return (
    <CorporateShell>
      <JsonLd data={buildLocalBusinessSchema()} />
      <ContactHero badge={t("hero.badge")} title={heroTitle} subtitle={heroSubtitle} />

      {isQuote && (
        <section className="site-section bg-white pt-0 pb-0">
          <Container size="narrow">
            <SlaResponseCountdown
              locale={locale}
              label={locale === "fr" ? "Réponse au devis d'ici" : "Quote response by"}
              expiredLabel={
                locale === "fr"
                  ? "Prochaine fenêtre de réponse imminente"
                  : "Next response window opens soon"
              }
            />
          </Container>
        </section>
      )}

      <section className="site-section bg-white -mt-2 relative z-10">
        <Container>
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-start">
            <FadeIn>
              <ContactInfoPanel info={contactInfo} />
              <GoogleBusinessProfileLink
                variant="contact"
                className="mt-6"
                label={tInfo("googleBusinessLabel")}
                reviewLabel={tInfo("googleReviewLabel")}
              />
            </FadeIn>
            <FadeIn delay={0.1}>
              <ContactInquiryForm intent={intent} attributionFrom={from} />
            </FadeIn>
          </div>
        </Container>
      </section>

      <ContactDepartmentCards
        label={t("departments.label")}
        title={t("departments.title")}
        items={departmentCards}
      />

      <FaqSection
        label={t("faq.label")}
        title={t("faq.title")}
        items={collectFaqItems(t, "faq.items", 5)}
        className="bg-white"
      />

      <ContactSocialBar label={t("social.label")} title={t("social.title")} />
    </CorporateShell>
  );
}
