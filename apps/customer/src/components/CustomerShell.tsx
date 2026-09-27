"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton } from "@clerk/nextjs";
import { Bell, Home, Plus, UserRound } from "lucide-react";
import { cn } from "@/lib/utils";
import { isClerkConfigured } from "@/lib/env";
import NotificationBell from "@/components/nav/NotificationBell";

const NAV = [
  { href: "/dashboard", label: "Home" },
  { href: "/book", label: "Book delivery" },
  { href: "/invoices", label: "Invoices" },
  { href: "/notifications", label: "Notifications" },
  { href: "/account", label: "Account" },
] as const;

const MOBILE_TABS = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/book", label: "Book", icon: Plus, primary: true },
  { href: "/account", label: "Account", icon: UserRound },
  { href: "/notifications", label: "Alerts", icon: Bell },
] as const;

/**
 * Responsive shell: full-width desktop nav; bottom tabs only on small phones.
 */
export default function CustomerShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-dvh overflow-x-clip bg-gray-bg">
      <header className="sticky top-0 z-40 border-b border-primary/8 bg-white/95 backdrop-blur-xl print:hidden">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3 pt-[max(0.75rem,env(safe-area-inset-top))] sm:px-6 sm:py-4">
          <div className="flex min-w-0 items-center gap-6">
            <Link href="/dashboard" className="flex min-w-0 items-center gap-2.5">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-secondary text-sm font-bold text-white sm:h-10 sm:w-10">
                P
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-bold text-primary">Porterchain</span>
                <span className="block text-[0.65rem] font-medium uppercase tracking-[0.14em] text-muted">
                  Customer
                </span>
              </span>
            </Link>
            <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
              {NAV.map((item) => {
                const active =
                  pathname === item.href ||
                  (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                      active
                        ? "bg-secondary/10 text-secondary"
                        : "text-muted hover:bg-white hover:text-primary"
                    )}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <Link
              href="/book"
              className="hidden rounded-xl bg-secondary px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#1d4ed8] sm:inline-flex md:hidden"
            >
              Book
            </Link>
            <NotificationBell />
            {isClerkConfigured() ? (
              <UserButton
                appearance={{
                  elements: {
                    avatarBox: "h-9 w-9",
                  },
                }}
              />
            ) : null}
          </div>
        </div>
      </header>

      <main className="mx-auto min-w-0 max-w-5xl px-4 pb-[calc(5.5rem+env(safe-area-inset-bottom))] pt-5 sm:px-6 sm:pt-8 md:pb-10">
        {children}
      </main>

      {/* Bottom tabs — phones only */}
      <nav
        className="fixed bottom-0 left-0 right-0 z-40 border-t border-primary/8 bg-white/95 px-3 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-2 backdrop-blur-xl print:hidden md:hidden"
        aria-label="Mobile"
      >
        <ul className="mx-auto grid max-w-md grid-cols-4 items-end gap-1">
          {MOBILE_TABS.map((tab) => {
            const active =
              pathname === tab.href ||
              (tab.href !== "/dashboard" && pathname.startsWith(`${tab.href}/`));
            const Icon = tab.icon;
            if ("primary" in tab && tab.primary) {
              return (
                <li key={tab.href} className="flex justify-center">
                  <Link
                    href={tab.href}
                    className="customer-shimmer relative -mt-5 flex h-14 w-14 items-center justify-center overflow-hidden rounded-2xl bg-secondary text-white shadow-lg shadow-secondary/35"
                    aria-label={tab.label}
                  >
                    <Icon className="relative z-10 h-6 w-6" strokeWidth={2.4} />
                    <span className="customer-shimmer-glow absolute inset-0" aria-hidden />
                  </Link>
                </li>
              );
            }
            return (
              <li key={tab.href}>
                <Link
                  href={tab.href}
                  className={cn(
                    "flex flex-col items-center gap-0.5 rounded-xl px-2 py-1.5 text-[0.65rem] font-semibold transition-colors",
                    active ? "text-secondary" : "text-muted"
                  )}
                >
                  <Icon
                    className={cn("h-5 w-5", active && "text-secondary")}
                    strokeWidth={active ? 2.4 : 2}
                  />
                  {tab.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}
