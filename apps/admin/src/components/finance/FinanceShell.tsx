"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { cn } from "@porterchain/ui/utils";
import AdminPage from "@/components/layout/AdminPage";

/** Finance = six places, in the order money moves. */
export const FINANCE_SECTIONS = [
  { href: "/finance/cash", label: "Cash" },
  { href: "/finance/invoices", label: "Invoices" },
  { href: "/finance/payments", label: "Payments" },
  { href: "/finance/driver-pay", label: "Driver Pay" },
  { href: "/pricing", label: "Pricing" },
  { href: "/finance/reports", label: "Reports" },
  { href: "/finance/analytics", label: "Analytics" },
] as const;

export function FinanceNav() {
  const pathname = usePathname() || "";
  return (
    <nav aria-label="Finance" className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-1">
      {FINANCE_SECTIONS.map((s) => {
        const active = pathname === s.href || pathname.startsWith(`${s.href}/`);
        return (
          <Link
            key={s.href}
            href={s.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "shrink-0 rounded-full px-4 py-2 text-sm font-semibold transition",
              active
                ? "bg-primary text-white"
                : "text-primary/70 hover:bg-primary/5 hover:text-primary"
            )}
          >
            {s.label}
          </Link>
        );
      })}
    </nav>
  );
}

/** Page frame: nav, title, one sentence, at most one primary action. */
export function FinanceShell({
  title,
  subtitle,
  primary,
  children,
}: {
  title: string;
  subtitle: string;
  primary?: ReactNode;
  children: ReactNode;
}) {
  return (
    <AdminPage>
      <div className="mx-auto w-full max-w-6xl space-y-8">
        <FinanceNav />
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-3xl font-bold tracking-tight text-primary">{title}</h1>
            <p className="mt-1 text-sm text-muted">{subtitle}</p>
          </div>
          {primary ? <div className="w-full sm:w-auto">{primary}</div> : null}
        </header>
        {children}
      </div>
    </AdminPage>
  );
}

export function PrimaryButton({
  children,
  onClick,
  disabled,
  type = "button",
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-secondary px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-secondary/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary disabled:opacity-50 sm:w-auto"
    >
      {children}
    </button>
  );
}

export function QuietButton({
  children,
  onClick,
  disabled,
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex min-h-10 items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold text-secondary hover:bg-secondary/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-secondary disabled:opacity-50"
    >
      {children}
    </button>
  );
}

/** The one number that matters on the screen. */
export function Hero({
  label,
  value,
  children,
}: {
  label: string;
  value: string;
  children?: ReactNode;
}) {
  return (
    <section className="rounded-3xl border border-primary/10 bg-white p-6 sm:p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">{label}</p>
      <p className="mt-2 text-5xl font-extrabold tracking-tight tabular-nums text-primary sm:text-6xl">
        {value}
      </p>
      {children ? <div className="mt-4">{children}</div> : null}
    </section>
  );
}

export function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "bad" | "good";
}) {
  return (
    <div className="min-w-0">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">{label}</p>
      <p
        className={cn(
          "mt-1 truncate text-2xl font-bold tabular-nums",
          tone === "bad" ? "text-red-700" : tone === "good" ? "text-emerald-700" : "text-primary"
        )}
      >
        {value}
      </p>
    </div>
  );
}

export function Section({
  title,
  aside,
  children,
}: {
  title: string;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-bold text-primary">{title}</h2>
        {aside}
      </div>
      <div className="rounded-3xl border border-primary/10 bg-white p-4 sm:p-6">{children}</div>
    </section>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="py-6 text-center text-sm text-muted">{children}</p>;
}
