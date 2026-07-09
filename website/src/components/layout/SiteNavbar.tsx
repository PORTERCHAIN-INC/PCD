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
import { navbarNavigation } from "@/data/navbar-navigation";
import { cn } from "@/lib/utils";

/** Pages with a dark hero at the top — navbar starts transparent over the hero. */
const DARK_HERO_PATHS = new Set(["/", "/business", "/careers", "/contact"]);

function isNavPathActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function SiteNavbar() {
  const t = useTranslations("corporate.nav");
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const isDarkHero = DARK_HERO_PATHS.has(pathname);
  /** Transparent only at top of dark-hero pages; otherwise solid brand bar. */
  const navTransparent = isDarkHero && !scrolled;
  /** Blue bar with white text — all light-background pages and scrolled dark heroes. */
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
      active ? "text-white bg-white/10" : "text-white/80 hover:text-white hover:bg-white/10"
    );

  const getDropdownChildLabel = (menuId: string, childId: string) =>
    t(`${menuId}Menu.${childId}` as Parameters<typeof t>[0]);

  const closeMobile = () => setMobileOpen(false);

  return (
    <header
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300",
        navTransparent
          ? "bg-transparent"
          : "bg-primary/95 backdrop-blur-xl border-b border-white/10 shadow-lg shadow-primary/15"
      )}
    >
      <Container as="nav" aria-label="Main">
        <div className="flex h-16 md:h-[4.5rem] items-center justify-between gap-4">
          <Link
            href="/"
            className="flex items-center gap-2.5 group shrink-0"
            aria-label="Porterchain home"
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-secondary to-blue-600 flex items-center justify-center shadow-lg shadow-secondary/30 group-hover:scale-105 transition-transform">
              <span className="text-white font-bold text-base">P</span>
            </div>
            <span className="text-lg font-bold tracking-tight text-white transition-colors">
              Porterchain
            </span>
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
                  label={t(item.id)}
                  href={item.href}
                  items={item.children}
                  getChildLabel={(childId) => getDropdownChildLabel(item.id, childId)}
                  linkClass={linkClass}
                  pathname={pathname}
                  navLight={false}
                />
              );
            })}
          </div>

          <div className="hidden xl:flex items-center gap-3 shrink-0">
            <LanguageSwitcher lightText />
            <SiteNavbarAuth navLight={false} linkClass={(href, active) => linkClass(active)} />
            <LinkButton href={quoteHref} size="sm" external={quoteExternal}>
              {quoteLabel}
            </LinkButton>
          </div>

          <button
            type="button"
            onClick={() => setMobileOpen(!mobileOpen)}
            className="xl:hidden p-2.5 rounded-xl min-w-[2.75rem] min-h-[2.75rem] flex items-center justify-center ml-auto text-white"
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
              "xl:hidden border-t overflow-hidden max-h-[calc(100dvh-4rem)] overflow-y-auto",
              navBlue
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
                      className="block px-4 py-3 text-sm font-medium text-white/90 rounded-xl hover:bg-white/10 hover:text-white"
                    >
                      {t(item.id)}
                    </Link>
                  );
                }

                return (
                  <NavDropdown
                    key={item.id}
                    variant="mobile"
                    label={t(item.id)}
                    href={item.href}
                    items={item.children}
                    getChildLabel={(childId) => getDropdownChildLabel(item.id, childId)}
                    linkClass={linkClass}
                    pathname={pathname}
                    navLight={false}
                    onNavigate={closeMobile}
                    mobileOnDarkBar
                  />
                );
              })}
              <div className="pt-4 mt-2 border-t border-white/10 flex flex-col gap-3">
                <LanguageSwitcher lightText />
                <SiteNavbarAuth
                  navLight={false}
                  linkClass={() =>
                    "text-center py-3 text-sm font-medium text-white/90 hover:text-white"
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
