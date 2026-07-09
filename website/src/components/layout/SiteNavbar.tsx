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
import { customerPortalBookUrl } from "@/data/portal-links";
import { cn } from "@/lib/utils";

const DARK_HERO_PATHS = new Set(["/", "/business", "/careers", "/contact"]);

export default function SiteNavbar() {
  const t = useTranslations("corporate.nav");
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const isHome = pathname === "/";
  const isDarkHero = DARK_HERO_PATHS.has(pathname);
  const navLight = scrolled || !isDarkHero;

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional route-change reset
    setMobileOpen(false);
  }, [pathname]);

  const quoteHref = customerPortalBookUrl;
  const quoteLabel = t("bookNow");
  const quoteExternal = true;

  const linkClass = (active?: boolean) =>
    cn(
      "px-3.5 py-2 text-sm font-medium rounded-lg transition-colors",
      navLight
        ? active
          ? "text-secondary bg-secondary/5"
          : "text-primary/75 hover:text-primary hover:bg-gray-bg"
        : active
          ? "text-white bg-white/10"
          : "text-white/80 hover:text-white hover:bg-white/10"
    );

  const primaryLinks = [
    { label: t("business"), href: "/business" as const, external: false },
    { label: t("vehiclePartnerPortal"), href: "/vehicle-partner" as const, external: false },
  ];

  return (
    <header
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300",
        navLight
          ? "bg-white/90 backdrop-blur-xl border-b border-primary/[0.06] shadow-sm"
          : "bg-transparent"
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
            <span
              className={cn(
                "text-lg font-bold tracking-tight transition-colors",
                navLight ? "text-primary" : "text-white"
              )}
            >
              Porterchain
            </span>
          </Link>

          <div className="hidden lg:flex items-center gap-1">
            {primaryLinks.map((link) =>
              link.external ? (
                <a
                  key={link.href}
                  href={link.href}
                  className={linkClass()}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {link.label}
                </a>
              ) : (
                <Link
                  key={link.href}
                  href={link.href}
                  className={linkClass(pathname === link.href)}
                >
                  {link.label}
                </Link>
              )
            )}
          </div>

          <div className="hidden lg:flex items-center gap-3 shrink-0">
            <LanguageSwitcher scrolled={navLight} />
            <SiteNavbarAuth navLight={navLight} linkClass={(href, active) => linkClass(active)} />
            <LinkButton href={quoteHref} size="sm" external={quoteExternal}>
              {quoteLabel}
            </LinkButton>
          </div>

          <button
            type="button"
            onClick={() => setMobileOpen(!mobileOpen)}
            className={cn(
              "lg:hidden p-2.5 rounded-xl min-w-[2.75rem] min-h-[2.75rem] flex items-center justify-center ml-auto",
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
            className="lg:hidden bg-white border-t border-primary/[0.06] overflow-hidden"
          >
            <div className="page-container py-4 space-y-1">
              {primaryLinks.map((link) =>
                link.external ? (
                  <a
                    key={link.href}
                    href={link.href}
                    onClick={() => setMobileOpen(false)}
                    className="block px-4 py-3 text-sm font-medium text-primary rounded-xl hover:bg-gray-bg"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {link.label}
                  </a>
                ) : (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setMobileOpen(false)}
                    className="block px-4 py-3 text-sm font-medium text-primary rounded-xl hover:bg-gray-bg"
                  >
                    {link.label}
                  </Link>
                )
              )}
              <div className="pt-4 mt-2 border-t border-primary/[0.06] flex flex-col gap-3">
                <LanguageSwitcher scrolled />
                <SiteNavbarAuth
                  navLight
                  linkClass={() => "text-center py-3 text-sm font-medium text-primary"}
                  onNavigate={() => setMobileOpen(false)}
                />
                <div onClick={() => setMobileOpen(false)}>
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
