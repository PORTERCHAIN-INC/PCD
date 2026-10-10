"use client";

import { createContext, useContext, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { UserButton } from "@clerk/nextjs";
import { ListOrdered, Search, Send, UserRound } from "lucide-react";
import { CommandPalette, type PaletteEntry } from "@porterchain/ui/app-nav";
import { RouteViewTransition } from "@porterchain/ui/view-transition";
import { cn } from "@/lib/utils";
import { isClerkConfigured } from "@/lib/env";
import NotificationBell from "@/components/nav/NotificationBell";

/** Three things, in the order customers need them: Send, Orders, Account. */
const NAV = [
  { href: "/send", label: "Send", icon: Send },
  { href: "/orders", label: "Orders", icon: ListOrdered },
  { href: "/account", label: "Account", icon: UserRound },
] as const;

/** ⌘K: every customer page, including ones without a tab. */
const PALETTE: PaletteEntry[] = [
  { href: "/send", label: "Send a delivery", group: "Go to", keywords: "book quote" },
  { href: "/orders", label: "My orders", group: "Go to", keywords: "history" },
  { href: "/track", label: "Track a delivery", group: "Go to", keywords: "tracking number" },
  { href: "/invoices", label: "Invoices & receipts", group: "Account", keywords: "billing pay" },
  { href: "/notifications", label: "Notifications", group: "Account" },
  { href: "/account", label: "Account & addresses", group: "Account", keywords: "profile privacy" },
];

const MOBILE_TABS = [
  { href: "/orders", label: "Orders", icon: ListOrdered },
  { href: "/send", label: "Send", icon: Send, primary: true },
  { href: "/account", label: "Account", icon: UserRound },
] as const;

/**
 * Responsive shell: full-width desktop nav; bottom tabs only on small phones.
 */
const CustomerShellContext = createContext(false);

export default function CustomerShell({ children }: { children: React.ReactNode }) {
  const nested = useContext(CustomerShellContext);
  const pathname = usePathname();
  const router = useRouter();
  const [cmdk, setCmdk] = useState(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCmdk((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  if (nested) return children;

  return (
    <CustomerShellContext.Provider value={true}>
      <div className="min-h-dvh overflow-x-clip bg-gray-bg">
        <header className="sticky top-0 z-40 border-b border-primary/8 bg-white/95 backdrop-blur-xl print:hidden">
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3 pt-[max(0.75rem,env(safe-area-inset-top))] sm:px-6 sm:py-4">
            <div className="flex min-w-0 items-center gap-6">
              <Link href="/send" className="flex min-w-0 items-center gap-2.5">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-sm font-bold text-white sm:h-10 sm:w-10">
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
                  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "relative flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                        active
                          ? "bg-primary text-white"
                          : "text-primary/70 hover:bg-white hover:text-primary"
                      )}
                    >
                      {active ? (
                        <span
                          className="absolute inset-x-3 -bottom-1 h-0.5 rounded bg-secondary"
                          aria-hidden
                        />
                      ) : null}
                      <Icon className="h-4 w-4" aria-hidden />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            </div>
            <div className="flex items-center gap-2 sm:gap-3">
              <button
                type="button"
                onClick={() => setCmdk(true)}
                aria-label="Search (Ctrl or Command K)"
                className="flex h-9 items-center gap-2 rounded-xl border border-primary/10 px-2.5 text-sm text-muted hover:border-primary/25"
              >
                <Search className="h-4 w-4" aria-hidden />
                <kbd className="hidden rounded border border-primary/15 px-1.5 text-[10px] sm:inline">
                  ⌘K
                </kbd>
              </button>
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
          <RouteViewTransition>{children}</RouteViewTransition>
        </main>

        {/* Bottom tabs — phones only */}
        <nav
          className="fixed bottom-0 left-0 right-0 z-40 border-t border-primary/8 bg-white/95 px-3 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-2 backdrop-blur-xl print:hidden md:hidden"
          aria-label="Mobile"
        >
          <ul className="mx-auto grid max-w-md grid-cols-3 items-end gap-1">
            {MOBILE_TABS.map((tab) => {
              const active = pathname === tab.href || pathname.startsWith(`${tab.href}/`);
              const Icon = tab.icon;
              if ("primary" in tab && tab.primary) {
                return (
                  <li key={tab.href} className="flex justify-center">
                    <Link
                      href={tab.href}
                      className="relative -mt-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-white shadow-lg shadow-primary/30"
                      aria-label={tab.label}
                    >
                      <Icon className="h-6 w-6" strokeWidth={2.4} />
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
                      active ? "text-primary" : "text-primary/60"
                    )}
                  >
                    <Icon className="h-5 w-5" strokeWidth={active ? 2.4 : 2} />
                    {tab.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>
      <CommandPalette
        entries={PALETTE}
        open={cmdk}
        onClose={() => setCmdk(false)}
        onSelect={(href) => router.push(href as never)}
      />
    </CustomerShellContext.Provider>
  );
}
