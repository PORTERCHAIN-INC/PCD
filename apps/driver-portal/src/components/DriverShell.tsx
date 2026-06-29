"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  AlertTriangle,
  Award,
  Car,
  FileText,
  GraduationCap,
  LayoutDashboard,
  LifeBuoy,
  MapPin,
  Shield,
  Wallet,
} from "lucide-react";
import { cn, formatCents } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/stops", label: "Today's Stops", icon: MapPin },
  { href: "/earnings", label: "Earnings", icon: Award },
  { href: "/wallet", label: "Wallet", icon: Wallet },
  { href: "/performance", label: "Performance", icon: Award },
  { href: "/vehicle", label: "Vehicle", icon: Car },
  { href: "/insurance", label: "Insurance", icon: Shield },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/training", label: "Training", icon: GraduationCap },
  { href: "/support", label: "Support", icon: LifeBuoy },
];

export default function DriverShell({
  children,
  walletCents,
}: {
  children: React.ReactNode;
  walletCents?: number;
}) {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div className="flex min-h-screen bg-[var(--gray-bg)]">
      <aside className="hidden w-64 shrink-0 border-r border-[var(--primary)]/10 bg-white lg:flex lg:flex-col">
        <div className="border-b border-[var(--primary)]/10 px-6 py-5">
          <Link href="/dashboard" className="text-lg font-bold text-[var(--primary)]">
            Porterchain
          </Link>
          <p className="mt-1 text-xs text-[var(--muted)]">Driver Platform</p>
          {walletCents !== undefined && (
            <p className="mt-2 text-sm font-semibold text-[var(--secondary)]">
              {formatCents(walletCents)}
            </p>
          )}
        </div>
        <nav className="flex-1 space-y-1 p-4">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                  active
                    ? "bg-[var(--secondary)]/10 text-[var(--secondary)]"
                    : "text-[var(--primary)]/70 hover:bg-[var(--gray-bg)]"
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-[var(--primary)]/10 p-4 space-y-2">
          <button
            type="button"
            onClick={() => router.push("/emergency")}
            className="flex w-full items-center gap-2 rounded-xl bg-red-600 px-3 py-2.5 text-sm font-semibold text-white"
          >
            <AlertTriangle className="h-4 w-4" />
            Emergency
          </button>
          <button
            type="button"
            onClick={() => {
              localStorage.removeItem("driver_access_token");
              router.push("/login");
            }}
            className="w-full text-left text-sm text-[var(--muted)]"
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 p-6">{children}</main>
    </div>
  );
}
