"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton } from "@clerk/nextjs";
import { cn } from "@/lib/utils";
import { isClerkConfigured } from "@/lib/env";
import NotificationBell from "@/components/nav/NotificationBell";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/book", label: "Book delivery" },
  { href: "/notifications", label: "Notifications" },
] as const;

export default function CustomerShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-gray-bg">
      <header className="border-b border-primary/10 bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-4 px-6 py-4">
          <div className="flex items-center gap-6">
            <Link href="/dashboard" className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary/10 text-lg font-bold text-secondary">
                P
              </div>
              <div>
                <p className="text-sm font-bold text-primary">Porterchain</p>
                <p className="text-xs text-muted">Customer portal</p>
              </div>
            </Link>
            <nav className="hidden items-center gap-1 sm:flex">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    pathname === item.href || pathname.startsWith(`${item.href}/`)
                      ? "bg-secondary/10 text-secondary"
                      : "text-muted hover:bg-gray-bg hover:text-primary"
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/book"
              className="rounded-xl bg-secondary px-4 py-2.5 text-sm font-semibold text-white hover:bg-secondary/90 sm:hidden"
            >
              Book
            </Link>
            <NotificationBell />
            {isClerkConfigured() && <UserButton />}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-4xl px-6 py-8">{children}</main>
    </div>
  );
}
