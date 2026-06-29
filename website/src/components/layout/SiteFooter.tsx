"use client";

import { useTranslations } from "next-intl";
import { Mail, ArrowRight } from "lucide-react";
import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import { OrganizedFooterLinks } from "@/components/layout/OrganizedFooterLinks";
import SocialLinks from "@/components/layout/SocialLinks";
import { driverPortalUrl, merchantPortalUrl } from "@/data/portal-links";
import type { FooterSectionId } from "@/data/footer-navigation";

export default function SiteFooter() {
  const t = useTranslations("siteFooter");
  const tLegacy = useTranslations("footer");
  const year = new Date().getFullYear();

  const getSectionTitle = (section: FooterSectionId | "legal") =>
    t(`sections.${section}.title`);
  const getLinkLabel = (section: FooterSectionId, id: string) =>
    t(`sections.${section}.links.${id}`);
  const getLegalLabel = (id: string) => t(`sections.legal.links.${id}`);

  return (
    <footer id="contact" className="bg-primary text-white">
      <div className="border-b border-white/10">
        <Container className="py-12 md:py-16">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-6 text-center sm:text-left">
            <div className="max-w-md mx-auto sm:mx-0">
              <h3 className="type-h3 font-bold text-white">{tLegacy("newsletterTitle")}</h3>
              <p className="text-white/60 mt-1 type-small">{tLegacy("newsletterSubtitle")}</p>
            </div>
            <div className="flex flex-col sm:flex-row w-full sm:w-auto gap-2 max-w-md mx-auto sm:mx-0">
              <div className="flex items-center gap-2 flex-1 sm:w-72 md:w-80 bg-white/10 rounded-xl px-4 py-3.5 min-h-[2.75rem] border border-white/10">
                <Mail className="w-4 h-4 text-white/40 shrink-0" />
                <input
                  type="email"
                  placeholder={tLegacy("emailPlaceholder")}
                  className="flex-1 min-w-0 bg-transparent type-small text-white placeholder:text-white/40 outline-none"
                />
              </div>
              <button
                type="button"
                className="px-6 py-3.5 min-h-[2.75rem] bg-secondary text-white type-button font-bold rounded-full hover:bg-[#1d4ed8] transition-colors cursor-pointer flex items-center justify-center gap-2 shrink-0"
              >
                {tLegacy("subscribe")}
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </Container>
      </div>

      <Container as="footer" className="py-12 md:py-16">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 mb-12">
          <div className="lg:col-span-3 text-center sm:text-left">
            <Link href="/" className="inline-flex items-center gap-2.5 mb-4">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-secondary to-blue-600 flex items-center justify-center">
                <span className="text-white font-bold text-lg">P</span>
              </div>
              <span className="text-xl font-bold">Porterchain</span>
            </Link>
            <p className="text-white/50 type-small leading-relaxed mb-4">{t("tagline")}</p>
            <p className="text-white/40 type-caption leading-relaxed mb-6">{t("address")}</p>
            <div className="flex gap-3 justify-center sm:justify-start">
              <SocialLinks variant="footer" />
            </div>
          </div>

          <div className="lg:col-span-9">
            <OrganizedFooterLinks
              getSectionTitle={getSectionTitle}
              getLinkLabel={getLinkLabel}
              getLegalLabel={getLegalLabel}
              titleClassName="type-label-bold text-white mb-1"
              linkClassName="text-white/50 type-small hover:text-white transition-colors"
            />
          </div>
        </div>

        <div className="pt-8 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-center sm:text-left">
            <p className="text-white/40 type-small">{t("copyright", { year })}</p>
            <p className="text-white/30 type-caption mt-1">{tLegacy("iconAttribution")}</p>
          </div>
          <div className="flex flex-wrap justify-center sm:justify-end gap-4 sm:gap-6">
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
          <p className="text-white/40 type-caption text-center sm:text-right">{t("contactLine")}</p>
        </div>
      </Container>
    </footer>
  );
}
