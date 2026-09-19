import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { redirect } from "next/navigation";
import { routing, type Locale } from "@/i18n/routing";
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
import ShimmerButton from "@/components/magic/shimmer-button";
import SlaResponseCountdown from "@/components/seo/SlaResponseCountdown";
import WhatsAppQuoteLink from "@/components/seo/WhatsAppQuoteLink";
import { collectFaqItems } from "@/lib/corporate-content";
import { buildQuoteWhatsAppMessage } from "@/lib/whatsapp";
import { TrendingUp, Headphones, Building2, Truck, Code2 } from "lucide-react";
import { JsonLd } from "@/components/seo";
import { buildLocalBusinessSchema } from "@/lib/seo/schema";

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

  if (intent === "quote") {
    const fromParam = from?.trim() || "contact";
    redirect(`/${locale as Locale}/sign-up?intent=quote&from=${encodeURIComponent(fromParam)}`);
  }

  const t = await getTranslations("corporate.contact");
  const tInfo = await getTranslations("corporate.contact.info");
  const tHero = await getTranslations("corporate.home.hero");

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
      <ContactHero badge={t("hero.badge")} title={t("hero.title")} subtitle={t("hero.subtitle")} />

      <section className="site-section relative z-10 -mt-2 bg-white">
        <Container>
          <div className="grid items-start gap-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:gap-16">
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
              <ContactInquiryForm />
              <div className="mt-6 rounded-3xl border border-primary/8 bg-[#F4F6FA] p-6 sm:p-8">
                <p className="pc-eyebrow text-secondary">{t("capacityCard.eyebrow")}</p>
                <h2 className="mt-2 text-xl font-semibold tracking-tight text-primary sm:text-2xl">
                  {t("capacityCard.title")}
                </h2>
                <p className="mt-3 text-sm leading-relaxed text-muted sm:text-base">
                  {t("capacityCard.body")}
                </p>
                <div className="mt-5">
                  <SlaResponseCountdown
                    locale={locale}
                    label={tHero("slaLabel")}
                    expiredLabel={tHero("slaExpired")}
                  />
                </div>
                <div className="mt-6">
                  <ShimmerButton
                    href="/sign-up?intent=quote&from=contact"
                    trackSource="contact-to-business"
                    showArrow
                    className="rounded-xl"
                  >
                    {t("capacityCard.cta")}
                  </ShimmerButton>
                </div>
                <div className="mt-4">
                  <WhatsAppQuoteLink
                    message={buildQuoteWhatsAppMessage({ source: "contact" })}
                    label={locale === "fr" ? "Continuer sur WhatsApp" : "Continue on WhatsApp"}
                    sourceSection="contact"
                  />
                </div>
              </div>
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
