"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useLocale, useTranslations } from "next-intl";
import { FaWhatsapp } from "react-icons/fa6";
import { Menu, X } from "lucide-react";
import { Link, usePathname } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";
import LanguageSwitcher from "@/components/layout/LanguageSwitcher";
import SiteNavbarAuth from "@/components/layout/SiteNavbarAuth";
import PorterchainWordmark from "@/components/brand/PorterchainWordmark";
import { navbarNavigation } from "@/data/navbar-navigation";
import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";
import { buildChatWhatsAppMessage, buildWhatsAppDeepLink } from "@/lib/whatsapp";
import { cn } from "@/lib/utils";

/** Pages with a dark hero at the top — navbar starts transparent with light text. */
const DARK_HERO_PATHS = new Set(["/", "/careers", "/contact"]);
/** Pages with a light hero — navbar starts glass with dark text. */
const LIGHT_HERO_PATHS = new Set(["/business", "/login", "/vehicle-partner"]);

function isNavPathActive(pathname: string, href: string) {
  const pathOnly = href.split("?")[0]?.split("#")[0] ?? href;
  return pathname === pathOnly || pathname.startsWith(`${pathOnly}/`);
}

export default function SiteNavbar() {
  const t = useTranslations("corporate.nav");
  const locale = useLocale();
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const isDarkHero = DARK_HERO_PATHS.has(pathname);
  const isLightHero = LIGHT_HERO_PATHS.has(pathname);
  /** Transparent at top of hero pages; solid bar after scroll or on inner pages. */
  const navTransparent = (isDarkHero || isLightHero) && !scrolled;
  /** Glass + dark text on light heroes (e.g. homepage). */
  const navLight = isLightHero && navTransparent;
  /** Navy bar with white text — scrolled heroes and default inner pages. */
  const navBlue = !navTransparent;

  const whatsappHref = buildWhatsAppDeepLink(buildChatWhatsAppMessage(locale));

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional route-change reset
    setMobileOpen(false);
    setScrolled(false);
  }, [pathname]);

  const quoteHref = "/sign-up?intent=quote&from=nav";
  const quoteLabel = t("bookNow");
  const quoteExternal = false;

  const linkClass = (active?: boolean) =>
    cn(
      "px-3.5 py-2 text-sm font-medium rounded-lg transition-colors",
      navLight
        ? active
          ? "text-secondary bg-secondary/10"
          : "text-primary/80 hover:text-primary hover:bg-gray-bg"
        : active
          ? "text-white bg-white/10"
          : "text-white/80 hover:text-white hover:bg-white/10"
    );

  const closeMobile = () => setMobileOpen(false);

  const navLinks = navbarNavigation.filter(
    (item): item is { type: "link"; id: string; href: string } => item.type === "link"
  );

  return (
    <header
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300",
        navLight
          ? "bg-white/85 backdrop-blur-xl border-b border-primary/6 shadow-sm shadow-primary/5"
          : navTransparent
            ? "bg-transparent"
            : "bg-primary/95 backdrop-blur-xl border-b border-white/10 shadow-lg shadow-primary/15"
      )}
    >
      <Container>
        <div className="flex items-center gap-3 h-[var(--nav-height)]">
          <Link
            href="/"
            className="shrink-0 mr-1"
            aria-label="Porterchain home"
            onClick={closeMobile}
          >
            <PorterchainWordmark tone={navLight ? "light" : "dark"} size="md" />
          </Link>

          <div className="hidden xl:flex items-center gap-0.5">
            {navLinks.map((item) => (
              <Link
                key={item.id}
                href={item.href}
                className={linkClass(isNavPathActive(pathname, item.href))}
              >
                {t(item.id)}
              </Link>
            ))}
          </div>

          <div className="hidden xl:flex items-center gap-3 shrink-0 ml-auto">
            <LanguageSwitcher lightText={!navLight} />
            <SiteNavbarAuth navLight={navLight} linkClass={(href, active) => linkClass(active)} />
            <LinkButton href={quoteHref} size="sm" external={quoteExternal}>
              {quoteLabel}
            </LinkButton>
          </div>

          <button
            type="button"
            onClick={() => setMobileOpen(!mobileOpen)}
            className={cn(
              "xl:hidden p-2.5 rounded-xl min-w-[2.75rem] min-h-[2.75rem] flex items-center justify-center ml-auto",
              navLight ? "text-primary" : "text-white"
            )}
            aria-label={t("toggleMenu")}
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </Container>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className={cn(
              "xl:hidden border-t overflow-hidden max-h-[calc(100dvh-var(--nav-height)-var(--safe-top))] overflow-y-auto overscroll-contain",
              navLight
                ? "bg-white border-primary/10"
                : navBlue
                  ? "bg-primary border-white/10"
                  : "bg-primary/95 backdrop-blur-xl border-white/10"
            )}
          >
            <div className="page-container py-4 space-y-0.5">
              {navLinks.map((item) => (
                <Link
                  key={item.id}
                  href={item.href}
                  onClick={closeMobile}
                  className={cn(
                    "block px-4 py-3 text-sm font-medium rounded-xl",
                    navLight
                      ? "text-primary/90 hover:bg-gray-bg hover:text-primary"
                      : "text-white/90 hover:bg-white/10 hover:text-white"
                  )}
                >
                  {t(item.id)}
                </Link>
              ))}
              <div
                className={cn(
                  "pt-4 mt-2 border-t flex flex-col gap-2.5",
                  navLight ? "border-primary/10" : "border-white/10"
                )}
              >
                <LanguageSwitcher lightText={!navLight} />

                <div
                  className={cn(
                    "rounded-2xl border p-3 space-y-2.5",
                    navLight ? "border-primary/10 bg-gray-bg/80" : "border-white/12 bg-white/[0.06]"
                  )}
                >
                  <SiteNavbarAuth
                    navLight={navLight}
                    linkClass={() =>
                      cn(
                        "flex min-h-[2.75rem] w-full items-center justify-center gap-2 rounded-xl border px-4 py-3 text-sm font-semibold transition-colors",
                        navLight
                          ? "border-primary/12 bg-white text-primary hover:border-secondary/30 hover:bg-secondary/5"
                          : "border-white/20 bg-white/10 text-white hover:bg-white/15"
                      )
                    }
                    onNavigate={closeMobile}
                  />

                  <a
                    href={whatsappHref}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={() => {
                      track(ANALYTICS_EVENTS.WHATSAPP_CHAT_CLICK, {
                        source_section: "mobile_nav_menu",
                      });
                      closeMobile();
                    }}
                    className="flex min-h-[2.75rem] w-full items-center justify-center gap-2 rounded-xl bg-[#25D366] px-4 py-3 text-sm font-semibold text-white shadow-sm transition-transform active:scale-[0.99] hover:bg-[#1ebe57]"
                  >
                    <FaWhatsapp className="h-5 w-5" aria-hidden />
                    {t("whatsappChat")}
                  </a>

                  <div onClick={closeMobile}>
                    <LinkButton
                      href={quoteHref}
                      className="w-full justify-center"
                      external={quoteExternal}
                    >
                      {quoteLabel}
                    </LinkButton>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
