"use client";

import type { ReactNode } from "react";
import { Plus_Jakarta_Sans } from "next/font/google";
import { platformLoginUrl } from "@porterchain/auth";
import { publicEnv } from "@/lib/env";

const authDisplay = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-customer-auth",
  display: "swap",
});

export type CustomerAuthMode = "sign-in" | "sign-up";

type Props = {
  title: string;
  subtitle: string;
  mode?: CustomerAuthMode;
  showPlatformLogin?: boolean;
  footer?: ReactNode;
  children: ReactNode;
};

/**
 * Customer portal auth chrome — brand plane + form, one composition.
 * Delivery / tracking messaging; Clerk widget stays the only interactive card.
 */
export function CustomerAuthScreen({
  title,
  subtitle,
  mode = "sign-in",
  showPlatformLogin = false,
  footer,
  children,
}: Props) {
  const platformUrl = showPlatformLogin ? platformLoginUrl(publicEnv.websiteUrl) : null;

  return (
    <div
      className={`${authDisplay.variable} relative flex min-h-dvh flex-col lg:flex-row`}
      style={{ fontFamily: "var(--font-customer-auth), system-ui, sans-serif" }}
    >
      <BrandPanel mode={mode} />

      <section className="relative z-10 flex flex-1 flex-col justify-center px-5 py-10 sm:px-8 lg:px-12 xl:px-16">
        <div className="customer-auth-rise mx-auto w-full max-w-[26rem]">
          <header className="mb-8 lg:mb-10">
            <p className="text-[0.68rem] font-semibold uppercase tracking-[0.24em] text-secondary lg:hidden">
              Customer
            </p>
            <h1 className="mt-3 text-[1.65rem] font-semibold tracking-tight text-primary sm:text-3xl lg:mt-0">
              {title}
            </h1>
            <p className="mt-2.5 text-sm leading-relaxed text-muted sm:text-[0.95rem]">
              {subtitle}
            </p>
            {platformUrl ? (
              <p className="mt-4 text-xs leading-relaxed text-muted">
                Prefer one login for every portal?{" "}
                <a
                  href={platformUrl}
                  className="font-semibold text-secondary underline-offset-2 transition-colors hover:text-[#1d4ed8] hover:underline"
                >
                  Use Platform sign-in
                </a>
              </p>
            ) : null}
          </header>

          <div
            className="customer-auth-form min-w-0 rounded-2xl border border-primary/8 bg-white p-5 sm:p-7"
            role="main"
          >
            {children}
          </div>

          {footer ? (
            <div className="mt-7 text-center text-xs leading-relaxed text-muted sm:text-left">
              {footer}
            </div>
          ) : null}

          <p className="mt-8 text-center text-[0.7rem] text-muted/80 sm:text-left">
            <a
              href={publicEnv.websiteUrl || "https://porterchain.com"}
              className="transition-colors hover:text-primary"
            >
              ← Back to Porterchain
            </a>
          </p>
        </div>
      </section>
    </div>
  );
}

function BrandPanel({ mode }: { mode: CustomerAuthMode }) {
  return (
    <aside className="relative isolate flex min-h-[38vh] flex-col justify-between overflow-hidden bg-primary px-6 py-8 text-white sm:px-10 sm:py-10 lg:min-h-dvh lg:w-[46%] lg:max-w-xl lg:px-12 lg:py-14 xl:w-[48%]">
      <div aria-hidden className="customer-auth-glow pointer-events-none absolute inset-0" />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.14]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.09) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.09) 1px, transparent 1px)",
          backgroundSize: "56px 56px",
          maskImage: "radial-gradient(ellipse 90% 70% at 30% 20%, black, transparent)",
        }}
      />

      <div className="relative z-10">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.24em] text-accent/90">
          Customer
        </p>
        <p className="customer-auth-brand mt-4 select-none text-[2rem] font-semibold tracking-[0.02em] sm:text-[2.35rem]">
          Porterchain
        </p>
      </div>

      <div className="relative z-10 mt-10 max-w-md lg:mt-0 lg:pb-4">
        <p className="customer-auth-rise text-xl font-semibold leading-snug tracking-tight text-white sm:text-2xl lg:text-[1.75rem]">
          {mode === "sign-up"
            ? "One place for every delivery that matters."
            : "Track deliveries, invoices, and support — clearly."}
        </p>
        <p className="customer-auth-rise-delay mt-4 max-w-sm text-sm leading-relaxed text-white/65">
          {mode === "sign-up"
            ? "Create an account to follow shipments and reach support when you need it."
            : "Not a courier app — your window into Porterchain capacity on the road."}
        </p>
      </div>

      <p className="relative z-10 mt-8 hidden text-[0.7rem] uppercase tracking-[0.18em] text-white/35 lg:block">
        Transportation Capacity Network
      </p>
    </aside>
  );
}

export function CustomerAuthLoading({ label = "Preparing sign-in…" }: { label?: string }) {
  return (
    <CustomerAuthScreen title="Just a moment" subtitle={label}>
      <div className="flex flex-col items-center gap-3 py-8" role="status">
        <span className="customer-auth-pulse h-9 w-9 rounded-full border-2 border-secondary/25 border-t-secondary" />
        <p className="text-sm text-muted">Loading…</p>
      </div>
    </CustomerAuthScreen>
  );
}
