"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import PorterchainWordmark from "@/components/marketing/brand/PorterchainWordmark";

export type PlatformAuthMode = "sign-in" | "sign-up";

type Props = {
  mode?: PlatformAuthMode;
  title: string;
  subtitle: string;
  footer?: ReactNode;
  children: ReactNode;
};

/**
 * Platform login / sign-up chrome — brand plane + form, one composition.
 * Used on porterchain.com for customer + merchant Clerk sessions.
 */
export default function PlatformAuthLayout({
  mode = "sign-in",
  title,
  subtitle,
  footer,
  children,
}: Props) {
  const t = useTranslations("login");
  const tBrand = useTranslations("common.brand");

  return (
    <div className="relative flex min-h-[calc(100dvh-var(--nav-height))] flex-col lg:flex-row">
      <aside className="relative isolate flex min-h-[36vh] flex-col justify-between overflow-hidden bg-primary px-6 py-8 text-white sm:px-10 sm:py-10 lg:min-h-[calc(100dvh-var(--nav-height))] lg:w-[46%] lg:max-w-xl lg:px-12 lg:py-14 xl:w-[48%]">
        <div aria-hidden className="platform-auth-glow pointer-events-none absolute inset-0" />
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
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.24em] text-[#60a5fa]/90">
            {t("eyebrow")}
          </p>
          <div className="platform-auth-brand mt-4">
            <PorterchainWordmark tone="dark" size="lg" />
          </div>
        </div>

        <div className="relative z-10 mt-10 max-w-md lg:mt-0 lg:pb-4">
          <p className="platform-auth-rise text-xl font-semibold leading-snug tracking-tight text-white sm:text-2xl lg:text-[1.75rem]">
            {mode === "sign-up" ? t("brandHeadlineSignUp") : t("brandHeadline")}
          </p>
          <p className="platform-auth-rise-delay mt-4 max-w-sm text-sm leading-relaxed text-white/65">
            {mode === "sign-up" ? t("brandBodySignUp") : t("brandBody")}
          </p>
        </div>

        <p className="relative z-10 mt-8 hidden text-[0.7rem] uppercase tracking-[0.18em] text-white/35 lg:block">
          {tBrand("networkLine")}
        </p>
      </aside>

      <section className="relative z-10 flex flex-1 flex-col justify-center bg-gray-bg px-5 py-10 sm:px-8 lg:px-12 xl:px-16">
        <div className="platform-auth-rise mx-auto w-full max-w-[26rem]">
          <header className="mb-8 lg:mb-10">
            <p className="text-[0.68rem] font-semibold uppercase tracking-[0.24em] text-secondary lg:hidden">
              {t("eyebrow")}
            </p>
            <h1 className="mt-3 text-[1.65rem] font-semibold tracking-tight text-primary sm:text-3xl lg:mt-0">
              {title}
            </h1>
            <p className="mt-2.5 text-sm leading-relaxed text-muted sm:text-[0.95rem]">
              {subtitle}
            </p>
          </header>

          <div
            className="platform-auth-form min-w-0 rounded-2xl border border-primary/8 bg-white p-5 sm:p-7"
            role="main"
          >
            {children}
          </div>

          {footer ? (
            <div className="mt-7 text-center text-xs leading-relaxed text-muted sm:text-left sm:text-sm">
              {footer}
            </div>
          ) : null}

          <p className="mt-8 text-center text-xs text-muted sm:text-left">
            <Link href="/" className="transition-colors hover:text-primary">
              ← {t("backHome")}
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}

export function PlatformAuthLoading({ title, label }: { title: string; label: string }) {
  return (
    <PlatformAuthLayout title={title} subtitle={label}>
      <div className="flex flex-col items-center gap-3 py-8" role="status">
        <span className="platform-auth-pulse h-9 w-9 rounded-full border-2 border-secondary/25 border-t-secondary" />
        <p className="text-sm text-muted">{label}</p>
      </div>
    </PlatformAuthLayout>
  );
}
