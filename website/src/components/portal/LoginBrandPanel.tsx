"use client";

import { Building2, Package, Shield, Truck } from "lucide-react";
import { useTranslations } from "next-intl";
import PorterchainWordmark from "@/components/brand/PorterchainWordmark";
import { cn } from "@/lib/utils";

const roles = [
  { key: "merchant", icon: Building2 },
  { key: "driver", icon: Truck },
  { key: "customer", icon: Package },
  { key: "staff", icon: Shield },
] as const;

export default function LoginBrandPanel({ className }: { className?: string }) {
  const t = useTranslations("login");

  return (
    <aside
      className={cn(
        "relative hidden lg:flex lg:min-h-[calc(100dvh-var(--nav-height)-var(--safe-top))] flex-col justify-between overflow-hidden bg-primary px-8 xl:px-14 py-10 xl:py-12",
        className
      )}
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.35]"
        aria-hidden
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, rgba(255,255,255,0.14) 1px, transparent 0)",
          backgroundSize: "28px 28px",
        }}
      />
      <div
        className="pointer-events-none absolute -top-24 -right-24 h-72 w-72 rounded-full bg-secondary/20 blur-3xl"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute bottom-0 left-0 h-56 w-56 rounded-full bg-accent/10 blur-3xl"
        aria-hidden
      />

      <div className="relative z-10">
        <PorterchainWordmark tone="dark" size="lg" />
        <p className="pc-eyebrow mt-10 text-accent">{t("eyebrow")}</p>
        <h1 className="mt-3 max-w-md text-[1.75rem] xl:text-[2.1rem] font-semibold tracking-tight text-white leading-[1.12]">
          {t("headline")}
        </h1>
        <p className="mt-4 max-w-md text-sm leading-relaxed text-white/65">{t("subtitle")}</p>
      </div>

      <div className="relative z-10 mt-10 grid grid-cols-2 gap-3">
        {roles.map(({ key, icon: Icon }) => (
          <div
            key={key}
            className="rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur-sm"
          >
            <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-xl bg-white/10">
              <Icon className="h-4 w-4 text-white" aria-hidden />
            </div>
            <p className="text-sm font-semibold text-white">{t(`roles.${key}.title`)}</p>
            <p className="mt-1 text-xs leading-relaxed text-white/55">
              {t(`roles.${key}.description`)}
            </p>
          </div>
        ))}
      </div>

      <p className="relative z-10 mt-10 text-xs text-white/45">{t("trustLine")}</p>
    </aside>
  );
}
