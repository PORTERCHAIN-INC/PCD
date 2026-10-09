import { getTranslations } from "next-intl/server";
import { Clock3, Mail, MapPin, Phone, ShoppingBag } from "lucide-react";
import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import SocialLinks from "@/components/layout/SocialLinks";
import PorterchainWordmark from "@/components/marketing/brand/PorterchainWordmark";
import FooterNewsletter from "@/components/layout/footer/FooterNewsletter";
import { driverPortalUrl, merchantPortalUrl } from "@/data/portal-links";
import {
  assertUniqueFooterHrefs,
  footerNavigation,
  footerSectionOrder,
} from "@/data/footer-navigation";
import { COVERAGE_FSA_COUNT } from "@/lib/seo/delivery-programmatic";
import { PUBLIC_CONTACT_PHONE_E164 } from "@/lib/google-business";

assertUniqueFooterHrefs();

/** Same public address the previous footer published (not the env-specific contact inbox). */
const FOOTER_EMAIL = "enterprise@porterchain.com";

const PORTALS: Record<string, string> = {
  __MERCHANT_PORTAL__: merchantPortalUrl,
  __DRIVER_PORTAL__: driverPortalUrl,
};

const linkClass =
  "inline-flex min-h-10 items-center sm:min-h-7 rounded text-sm text-white/70 transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white";

function formatPhone(e164: string): string {
  const d = e164.replace(/\D/g, "").slice(-10);
  return `+1 (${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}`;
}

/**
 * Server-rendered site footer: one <footer> (contentinfo) landmark, one labelled <nav>, five
 * grouped columns. Only the newsletter form hydrates.
 */
export default async function SiteFooter() {
  const t = await getTranslations("siteFooter");
  const email = FOOTER_EMAIL;
  const year = 2026;

  return (
    <footer className="bg-primary text-white" aria-label={t("ariaLabel")}>
      <div className="border-b border-white/10">
        <Container className="py-10 md:py-12">
          <FooterNewsletter />
        </Container>
      </div>

      <Container className="py-12 md:py-16">
        <div className="grid gap-10 lg:grid-cols-12 lg:gap-12">
          <div className="lg:col-span-4">
            <Link
              href="/"
              aria-label="PorterChain home"
              className="inline-flex rounded transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            >
              <PorterchainWordmark tone="dark" size="lg" />
            </Link>
            <p
              className="mt-4 flex gap-2 text-sm leading-relaxed text-white/80"
              data-testid="footer-coverage"
            >
              <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-[#93c5fd]" aria-hidden />
              {t("coverage", { count: COVERAGE_FSA_COUNT })}
            </p>
            <address className="mt-5 space-y-2 text-sm not-italic text-white/80">
              <p className="text-xs font-semibold uppercase tracking-wide text-white/60">
                {t("contactTitle")}
              </p>
              <p className="flex items-center gap-2">
                <Mail className="h-4 w-4 shrink-0 text-white/60" aria-hidden />
                <span className="sr-only">{t("emailLabel")}: </span>
                <a href={`mailto:${email}`} className={linkClass}>
                  {email}
                </a>
              </p>
              <p className="flex items-center gap-2">
                <Phone className="h-4 w-4 shrink-0 text-white/60" aria-hidden />
                <span className="sr-only">{t("phoneLabel")}: </span>
                <a href={`tel:${PUBLIC_CONTACT_PHONE_E164}`} className={linkClass}>
                  {formatPhone(PUBLIC_CONTACT_PHONE_E164)}
                </a>
              </p>
              <p className="flex items-start gap-2" data-testid="footer-hours">
                <Clock3 className="mt-0.5 h-4 w-4 shrink-0 text-white/60" aria-hidden />
                <span>
                  <span className="sr-only">{t("hoursLabel")}: </span>
                  {t("hours")}
                </span>
              </p>
            </address>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <Link
                href="/delivery/shopify-merchants"
                className="inline-flex min-h-11 items-center gap-2 rounded-full border border-white/20 bg-white/5 px-4 text-sm font-medium text-white transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
                data-testid="footer-shopify-badge"
              >
                <ShoppingBag className="h-4 w-4 text-[#95bf47]" aria-hidden />
                <span>{t("shopifyBadge")}</span>
                <span className="text-white/60">· {t("shopifyBadgeHint")}</span>
              </Link>
            </div>
            <div className="mt-6">
              <SocialLinks variant="footer" />
            </div>
          </div>

          <nav aria-label={t("navLabel")} className="lg:col-span-8">
            <div className="grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-3 lg:grid-cols-5">
              {footerSectionOrder.map((section) => (
                <div key={section}>
                  <h2 className="text-sm font-semibold text-white">
                    {t(`sections.${section}.title`)}
                  </h2>
                  <ul className="mt-2 space-y-0.5 sm:space-y-1">
                    {footerNavigation[section].map((link) => {
                      const label = link.label ?? t(`sections.${section}.links.${link.id}`);
                      const external = PORTALS[link.href];
                      return (
                        <li key={link.href}>
                          {external ? (
                            <a href={external} className={linkClass}>
                              {label}
                            </a>
                          ) : (
                            <Link href={link.href} className={linkClass}>
                              {label}
                            </Link>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ))}
            </div>
          </nav>
        </div>

        <div className="mt-12 flex flex-col gap-2 border-t border-white/10 pt-8 text-xs text-white/60 sm:flex-row sm:justify-between">
          <p>{t("copyright", { year })}</p>
        </div>
      </Container>
    </footer>
  );
}
