"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  CreditCard,
  FileSpreadsheet,
  Key,
  LayoutDashboard,
  Package,
  Settings,
  Truck,
  Users,
} from "lucide-react";
import { UserButton } from "@clerk/nextjs";
import { cn } from "@/lib/utils";
import Container from "@/components/ui/Container";
import { isClerkConfigured } from "@/lib/env";

const NAV = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/book", label: "Book Delivery", icon: Truck },
  { href: "/bulk", label: "Bulk Upload", icon: FileSpreadsheet },
  { href: "/orders", label: "Orders", icon: Package },
  { href: "/track", label: "Track", icon: Truck },
  { href: "/billing", label: "Billing", icon: CreditCard },
  { href: "/reports", label: "Reports", icon: BarChart3 },
  { href: "/api", label: "API & Webhooks", icon: Key },
  { href: "/team", label: "Team", icon: Users },
  { href: "/settings", label: "Business Profile", icon: Settings },
];

export default function PortalShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen bg-gray-bg">
      <aside className="hidden w-64 shrink-0 border-r border-primary/10 bg-white lg:flex lg:flex-col">
        <div className="border-b border-primary/10 px-6 py-5">
          <Link href="/dashboard" className="text-lg font-bold text-primary">
            Porterchain
          </Link>
          <p className="mt-1 text-xs text-muted">Merchant Portal</p>
        </div>
        <nav className="flex-1 space-y-1 p-4">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                  active
                    ? "bg-secondary/10 text-secondary"
                    : "text-primary/70 hover:bg-gray-bg hover:text-primary"
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-primary/10 p-4">
          {isClerkConfigured() ? (
            <UserButton />
          ) : (
            <Link href="/sign-in" className="text-sm text-secondary">
              Sign in
            </Link>
          )}
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-primary/10 bg-white px-4 py-3 lg:hidden">
          <Link href="/dashboard" className="font-bold text-primary">
            Porterchain
          </Link>
          {isClerkConfigured() ? (
            <UserButton />
          ) : (
            <Link href="/sign-in" className="text-sm text-secondary">
              Sign in
            </Link>
          )}
        </header>
        <main className="flex-1 py-6">
          <Container>{children}</Container>
        </main>
      </div>
    </div>
  );
}
