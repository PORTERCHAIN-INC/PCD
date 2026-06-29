"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Building2,
  CreditCard,
  Headphones,
  LayoutDashboard,
  Map,
  Package,
  Settings,
  Shield,
  Truck,
  Users,
  Zap,
} from "lucide-react";
import { UserButton } from "@clerk/nextjs";
import Container from "@porterchain/ui/container";
import { cn } from "@porterchain/ui/utils";
import { isClerkConfigured } from "@/lib/env";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/crm", label: "CRM", icon: Users },
  { href: "/merchants", label: "Merchants", icon: Building2 },
  { href: "/drivers", label: "Drivers", icon: Truck },
  { href: "/operations", label: "Operations", icon: Zap },
  { href: "/map", label: "Live Map", icon: Map },
  { href: "/orders", label: "Orders", icon: Package },
  { href: "/claims", label: "Claims", icon: Shield },
  { href: "/pricing", label: "Pricing", icon: CreditCard },
  { href: "/finance", label: "Finance", icon: CreditCard },
  { href: "/support", label: "Support", icon: Headphones },
  { href: "/reports", label: "Reports", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="flex min-h-screen bg-gray-bg">
      <aside className="hidden w-64 shrink-0 border-r border-primary/10 bg-white lg:flex lg:flex-col">
        <div className="border-b border-primary/10 px-6 py-5">
          <p className="text-lg font-bold text-primary">Porterchain</p>
          <p className="text-xs text-muted">Admin & Operations</p>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-4">
          {NAV.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium",
                pathname === href || pathname.startsWith(`${href}/`)
                  ? "bg-secondary/10 text-secondary"
                  : "text-primary/70 hover:bg-gray-bg"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          ))}
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
      <main className="min-w-0 flex-1 py-6">
        <Container>{children}</Container>
      </main>
    </div>
  );
}
