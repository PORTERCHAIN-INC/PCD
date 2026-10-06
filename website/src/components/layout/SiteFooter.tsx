"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Mail, ArrowRight } from "lucide-react";
import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import { OrganizedFooterLinks } from "@/components/layout/OrganizedFooterLinks";
import SocialLinks from "@/components/layout/SocialLinks";
import GoogleBusinessProfileLink from "@/components/integrations/GoogleBusinessProfileLink";
import PorterchainWordmark from "@/components/marketing/brand/PorterchainWordmark";
import { driverPortalUrl, merchantPortalUrl } from "@/data/portal-links";
import { submitInquiry } from "@/lib/submit-inquiry";
import type { FooterSectionId } from "@/data/footer-navigation";

export default function SiteFooter() {
  const t = useTranslations("siteFooter");
  const tBrand = useTranslations("common.brand");
  const tLegacy = useTranslations("footer");
  // Stable across prerender — Cache Components forbids Date() in the client shell.
  const year = 2026;
  const [newsletterEmail, setNewsletterEmail] = useState("");
  const [newsletterLoading, setNewsletterLoading] = useState(false);
  const [newsletterDone, setNewsletterDone] = useState(false);
  const [newsletterError, setNewsletterError] = useState<string | null>(null);

  const getSectionTitle = (section: FooterSectionId) => t(`sections.${section}.title`);
  const getLinkLabel = (section: FooterSectionId, id: string) =>
    t(`sections.${section}.links.${id}`);

  async function handleNewsletterSubmit(e: React.FormEvent) {
    e.preventDefault();
    const email = newsletterEmail.trim();
    if (!email) return;

    setNewsletterLoading(true);
    setNewsletterError(null);
    try {
      await submitInquiry({
        email,
        source: "website",
        source_page: "/footer-newsletter",
        form: "newsletter",
        inquiry_type: "newsletter",
        message: "Newsletter subscription from site footer",
      });
      setNewsletterDone(true);
      setNewsletterEmail("");
    } catch {
      setNewsletterError(tLegacy("newsletterError"));
    } finally {
      setNewsletterLoading(false);
    }
  }

  return (
    <footer className="bg-primary text-white">
      <div className="border-b border-white/10">
        <Container className="py-12 md:py-16">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-6 text-center sm:text-left">
            <div className="max-w-md mx-auto sm:mx-0">
              <h3 className="type-h3 font-bold text-white">{tLegacy("newsletterTitle")}</h3>
              <p className="text-white/60 mt-1 type-small">{tLegacy("newsletterSubtitle")}</p>
            </div>
            <form
              onSubmit={handleNewsletterSubmit}
              className="flex flex-col sm:flex-row w-full sm:w-auto gap-2 max-w-md mx-auto sm:mx-0"
              suppressHydrationWarning
            >
              {newsletterDone ? (
                <p className="text-sm text-secondary font-medium py-3">{tLegacy("subscribed")}</p>
              ) : (
                <>
                  <div className="flex items-center gap-2 flex-1 sm:w-72 md:w-80 bg-white/10 rounded-xl px-4 py-3.5 min-h-[2.75rem] border border-white/10">
                    <Mail className="w-4 h-4 text-white/40 shrink-0" />
                    <input
                      type="email"
                      required
                      value={newsletterEmail}
                      onChange={(e) => setNewsletterEmail(e.target.value)}
                      placeholder={tLegacy("emailPlaceholder")}
                      className="flex-1 min-w-0 bg-transparent type-small text-white placeholder:text-white/40 outline-none"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={newsletterLoading}
                    className="px-6 py-3.5 min-h-[2.75rem] bg-secondary text-white type-button font-bold rounded-full hover:bg-[#1d4ed8] transition-colors cursor-pointer flex items-center justify-center gap-2 shrink-0 disabled:opacity-50"
                  >
                    {newsletterLoading ? tLegacy("subscribing") : tLegacy("subscribe")}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </>
              )}
            </form>
            {newsletterError && (
              <p className="mt-2 text-sm text-red-300 text-center sm:text-left">
                {newsletterError}
              </p>
            )}
          </div>
        </Container>
      </div>

      <Container as="footer" className="py-12 md:py-16">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 mb-12">
          <div className="lg:col-span-3 text-center sm:text-left">
            <Link
              href="/"
              aria-label="Porterchain"
              className="inline-flex mb-4 max-w-full transition-opacity hover:opacity-90"
            >
              <PorterchainWordmark tone="dark" size="lg" />
            </Link>
            <p className="text-white/50 type-small leading-relaxed mb-1">{tBrand("networkLine")}</p>
            <p className="text-white/50 type-small leading-relaxed mb-6">{t("tagline")}</p>
            <div className="flex gap-3 justify-center sm:justify-start flex-wrap items-center">
              <SocialLinks variant="footer" />
              <GoogleBusinessProfileLink
                variant="footer"
                label={t("googleBusiness")}
                reviewLabel={t("googleReview")}
                showReview
              />
            </div>
          </div>

          <div className="lg:col-span-9">
            <OrganizedFooterLinks
              getSectionTitle={getSectionTitle}
              getLinkLabel={getLinkLabel}
              titleClassName="type-label-bold text-white mb-1"
              linkClassName="text-white/50 type-small hover:text-white transition-colors"
            />
          </div>
        </div>

        <div className="pt-8 border-t border-white/10 flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="text-center sm:text-left space-y-1">
            <p className="text-white/40 type-small">{t("copyright", { year })}</p>
            <p className="text-white/40 type-caption">{t("contactLine")}</p>
          </div>
          <div className="flex flex-wrap justify-center lg:justify-end gap-4 sm:gap-6">
            <a
              href={merchantPortalUrl}
              className="text-white/50 type-small hover:text-white transition-colors"
            >
              {t("merchantPortal")}
            </a>
            <a
              href={driverPortalUrl}
              className="text-white/50 type-small hover:text-white transition-colors"
            >
              {t("driverPortal")}
            </a>
            <Link
              href="/contact"
              className="text-white/50 type-small hover:text-white transition-colors"
            >
              {t("support")}
            </Link>
          </div>
        </div>
      </Container>
    </footer>
  );
}
