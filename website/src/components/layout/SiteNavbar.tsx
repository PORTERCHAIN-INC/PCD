"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { FaWhatsapp } from "react-icons/fa6";
import { Menu, X } from "lucide-react";
import { Link, usePathname } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/marketing/corporate/ui/LinkButton";
import LanguageSwitcher from "@/components/layout/LanguageSwitcher";
import SiteNavbarAuth from "@/components/layout/SiteNavbarAuth";
import PorterchainWordmark from "@/components/marketing/brand/PorterchainWordmark";
import { navbarNavigation } from "@/data/navbar-navigation";
import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";
import { buildChatWhatsAppMessage, buildWhatsAppDeepLink } from "@/lib/whatsapp";
import { cn } from "@/lib/utils";

/** Pages with a dark hero at the top — navbar starts transparent with light text. */
const DARK_HERO_PATHS = new Set(["/", "/careers", "/contact"]);
/** Pages with a light hero — navbar starts glass with dark text. */
const LIGHT_HERO_PATHS = new Set(["/business", "/login", "/vehicle-partner"]);

const MOBILE_MENU_ID = "site-mobile-menu";

function isNavPathActive(pathname: string, href: string) {
  const pathOnly = href.split("?")[0]?.split("#")[0] ?? href;
  return pathname === pathOnly || pathname.startsWith(`${pathOnly}/`);
}

/**
 * Site header — five top links (Price, Industries, Track, Shopify app, Sign in) + "Book now".
 * No framer-motion: the mobile sheet is plain CSS (`.nav-sheet`, reduced-motion safe), which
 * keeps the animation library out of the shared bundle on pages that do not otherwise use it.
 */
export default function SiteNavbar() {
  const t = useTranslations("corporate.nav");
  const locale = useLocale();
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const isDarkHero = DARK_HERO_PATHS.has(pathname);
  const isLightHero = LIGHT_HERO_PATHS.has(pathname);
  /** Transparent at top of hero pages; solid bar after scroll or on inner pages. */
  const navTransparent = (isDarkHero || isLightHero) && !scrolled && !mobileOpen;
  /** Glass + dark text on light heroes. */
  const navLight = isLightHero && navTransparent;

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

  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileOpen]);

  const quoteHref = "/sign-up?intent=quote&from=nav";
  const quoteLabel = t("book");

  const focusRing = navLight
    ? "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2"
    : "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-primary";

  const linkClass = (active?: boolean) =>
    cn(
      "px-3 py-2 text-sm font-medium rounded-lg transition-colors",
      focusRing,
      navLight
        ? active
          ? "text-secondary bg-secondary/10"
          : "text-primary/80 hover:text-primary hover:bg-gray-bg"
        : active
          ? "text-white bg-white/10"
          : "text-white/85 hover:text-white hover:bg-white/10"
    );

  const closeMobile = () => setMobileOpen(false);

  const navLinks = navbarNavigation.filter(
    (item): item is { type: "link"; id: string; href: string } => item.type === "link"
  );

  return (
    <header
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-[background-color,box-shadow,border-color] duration-300",
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
            className={cn("shrink-0 mr-2 rounded-lg", focusRing)}
            aria-label="Porterchain home"
            onClick={closeMobile}
          >
            <PorterchainWordmark tone={navLight ? "light" : "dark"} size="md" />
          </Link>

          <nav aria-label={t("primaryNavLabel")} className="hidden lg:flex items-center gap-0.5">
            {navLinks.map((item) => {
              const active = isNavPathActive(pathname, item.href);
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={linkClass(active)}
                >
                  {t(item.id)}
                </Link>
              );
            })}
            <SiteNavbarAuth navLight={navLight} linkClass={(href, active) => linkClass(active)} />
          </nav>

          <div className="hidden lg:flex items-center gap-3 shrink-0 ml-auto">
            <LanguageSwitcher lightText={!navLight} />
            <LinkButton href={quoteHref} size="sm" trackSource="nav" trackLabel="book_now">
              {quoteLabel}
            </LinkButton>
          </div>

          {/* Always-visible booking CTA on mobile/tablet header (readiness audit #10). */}
          <div className="lg:hidden ml-auto shrink-0">
            <LinkButton
              href={quoteHref}
              size="sm"
              trackSource="nav_mobile"
              trackLabel="book_now"
              className="min-h-[2.75rem] px-4 whitespace-nowrap"
            >
              {quoteLabel}
            </LinkButton>
          </div>

          <button
            type="button"
            onClick={() => setMobileOpen(!mobileOpen)}
            className={cn(
              "lg:hidden p-2.5 rounded-xl min-w-[2.75rem] min-h-[2.75rem] flex items-center justify-center",
              focusRing,
              navLight ? "text-primary" : "text-white"
            )}
            aria-label={t("toggleMenu")}
            aria-expanded={mobileOpen}
            aria-controls={MOBILE_MENU_ID}
          >
            {mobileOpen ? (
              <X className="w-5 h-5" aria-hidden />
            ) : (
              <Menu className="w-5 h-5" aria-hidden />
            )}
          </button>
        </div>
      </Container>

      {mobileOpen ? (
        <div
          id={MOBILE_MENU_ID}
          className="nav-sheet lg:hidden border-t border-white/10 bg-primary max-h-[calc(100dvh-var(--nav-height)-var(--safe-top))] overflow-y-auto overscroll-contain"
        >
          <nav aria-label={t("primaryNavLabel")} className="page-container py-4 space-y-0.5">
            {navLinks.map((item) => {
              const active = isNavPathActive(pathname, item.href);
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  onClick={closeMobile}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex min-h-[2.75rem] items-center px-4 py-3 text-base font-medium rounded-xl",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white",
                    active
                      ? "bg-white/10 text-white"
                      : "text-white/90 hover:bg-white/10 hover:text-white"
                  )}
                >
                  {t(item.id)}
                </Link>
              );
            })}
            <div className="pt-4 mt-2 border-t border-white/10 flex flex-col gap-2.5">
              <LanguageSwitcher lightText />

              <div className="rounded-2xl border border-white/12 bg-white/[0.06] p-3 space-y-2.5">
                <SiteNavbarAuth
                  navLight={false}
                  linkClass={() =>
                    cn(
                      "flex min-h-[2.75rem] w-full items-center justify-center gap-2 rounded-xl border px-4 py-3 text-sm font-semibold transition-colors",
                      "border-white/20 bg-white/10 text-white hover:bg-white/15",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
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
                  className="flex min-h-[2.75rem] w-full items-center justify-center gap-2 rounded-xl bg-[#25D366] px-4 py-3 text-sm font-semibold text-primary shadow-sm transition-transform active:scale-[0.99] hover:bg-[#1ebe57] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
                >
                  <FaWhatsapp className="h-5 w-5" aria-hidden />
                  {t("whatsappChat")}
                </a>

                <div onClick={closeMobile}>
                  <LinkButton
                    href={quoteHref}
                    className="w-full justify-center"
                    trackSource="nav_menu"
                    trackLabel="book_now"
                  >
                    {quoteLabel}
                  </LinkButton>
                </div>
              </div>
            </div>
          </nav>
        </div>
      ) : null}
    </header>
  );
}
