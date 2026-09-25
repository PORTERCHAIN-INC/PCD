"use client";

import { useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import { SOLUTIONS_TAB_ITEMS, isSolutionsTabActive } from "@/data/solutions-navigation";
import { cn } from "@/lib/utils";

export default function SolutionsTabNav() {
  const t = useTranslations("corporate.nav.solutionsTabs");
  const pathname = usePathname();
  const scrollerRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ inline: "center", block: "nearest", behavior: "smooth" });
  }, [pathname]);

  return (
    <nav
      aria-label={t("ariaLabel")}
      className="sticky top-[var(--nav-height)] z-40 border-b border-primary/[0.08] bg-white/95 backdrop-blur-md"
    >
      <Container className="py-0">
        <div
          ref={scrollerRef}
          className="flex gap-1 overflow-x-auto overscroll-x-contain scrollbar-hide -mx-1 px-1"
          role="tablist"
        >
          {SOLUTIONS_TAB_ITEMS.map((item) => {
            const active = isSolutionsTabActive(pathname, item);
            return (
              <Link
                key={item.id}
                ref={active ? activeRef : undefined}
                href={item.href}
                role="tab"
                aria-selected={active}
                className={cn(
                  "relative shrink-0 px-3.5 py-3 text-sm font-medium transition-colors whitespace-nowrap",
                  active ? "text-secondary" : "text-muted hover:text-primary"
                )}
              >
                {t(item.id)}
                {active && (
                  <span
                    className="absolute inset-x-2 bottom-0 h-0.5 rounded-full bg-secondary"
                    aria-hidden
                  />
                )}
              </Link>
            );
          })}
        </div>
      </Container>
    </nav>
  );
}
