"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslations } from "next-intl";
import { Menu, X } from "lucide-react";
import { Link, usePathname } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";
import LanguageSwitcher from "@/components/layout/LanguageSwitcher";
import SiteNavbarAuth from "@/components/layout/SiteNavbarAuth";
import NavDropdown from "@/components/layout/NavDropdown";
import PorterchainWordmark from "@/components/brand/PorterchainWordmark";
import { navbarNavigation } from "@/data/navbar-navigation";
import { isVehiclesNavActive } from "@/data/vehicles-navigation";
import { cn } from "@/lib/utils";

/** Pages with a dark hero at the top — navbar starts transparent with light text. */
const DARK_HERO_PATHS = new Set(["/", "/careers", "/contact"]);
/** Pages with a light hero — navbar starts glass with dark text. */
const LIGHT_HERO_PATHS = new Set(["/business", "/login", "/vehicle-partner"]);

function isNavPathActive(pathname: string, href: string) {
  const pathOnly = href.split("?")[0] ?? href;
  if (pathOnly === "/solutions") {
    return (
      pathname === "/solutions" ||
      pathname.startsWith("/solutions/") ||
      pathname === "/construction" ||
      pathname.startsWith("/construction/")
    );
  }
  if (pathOnly === "/vehicles") {
    return isVehiclesNavActive(pathname);
  }
  return pathname === pathOnly || pathname.startsWith(`${pathOnly}/`);
}

export default function SiteNavbar() {
  const t = useTranslations("corporate.nav");
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

  const quoteHref = "/contact?intent=quote";
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

  const getDropdownChildLabel = (menuId: string, childId: string) =>
    t(`${menuId}Menu.${childId}.label` as Parameters<typeof t>[0]);

  const getDropdownChildDescription = (menuId: string, childId: string) =>
    t(`${menuId}Menu.${childId}.description` as Parameters<typeof t>[0]);

  const closeMobile = () => setMobileOpen(false);

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
      <Container as="nav" aria-label="Main">
        <div className="flex h-16 md:h-[4.5rem] items-center justify-between gap-4">
          <Link
            href="/"
            className="group shrink-0 transition-opacity hover:opacity-90"
            aria-label="Porterchain home"
          >
            <PorterchainWordmark tone={navLight ? "light" : "dark"} size="md" />
          </Link>

          <div className="hidden xl:flex items-center gap-0.5">
            {navbarNavigation.map((item) => {
              if (item.type === "link") {
                return (
                  <Link
                    key={item.id}
                    href={item.href}
                    className={linkClass(isNavPathActive(pathname, item.href))}
                  >
                    {t(item.id)}
                  </Link>
                );
              }

              return (
                <NavDropdown
                  key={item.id}
                  menuId={item.id}
                  label={t(item.id)}
                  href={item.href}
                  items={item.children}
                  getChildLabel={(childId) => getDropdownChildLabel(item.id, childId)}
                  getChildDescription={(childId) => getDropdownChildDescription(item.id, childId)}
                  linkClass={linkClass}
                  pathname={pathname}
                  navLight={navLight}
                />
              );
            })}
          </div>

          <div className="hidden xl:flex items-center gap-3 shrink-0">
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
              {navbarNavigation.map((item) => {
                if (item.type === "link") {
                  return (
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
                  );
                }

                return (
                  <NavDropdown
                    key={item.id}
                    variant="mobile"
                    menuId={item.id}
                    label={t(item.id)}
                    href={item.href}
                    items={item.children}
                    getChildLabel={(childId) => getDropdownChildLabel(item.id, childId)}
                    getChildDescription={(childId) => getDropdownChildDescription(item.id, childId)}
                    linkClass={linkClass}
                    pathname={pathname}
                    navLight={navLight}
                    onNavigate={closeMobile}
                    mobileOnDarkBar={!navLight}
                  />
                );
              })}
              <div
                className={cn(
                  "pt-4 mt-2 border-t flex flex-col gap-3",
                  navLight ? "border-primary/10" : "border-white/10"
                )}
              >
                <LanguageSwitcher lightText={!navLight} />
                <SiteNavbarAuth
                  navLight={navLight}
                  linkClass={() =>
                    navLight
                      ? "text-center py-3 text-sm font-medium text-primary/90 hover:text-primary"
                      : "text-center py-3 text-sm font-medium text-white/90 hover:text-white"
                  }
                  onNavigate={closeMobile}
                />
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
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
