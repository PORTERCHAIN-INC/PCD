"use client";

import { SignIn } from "@clerk/nextjs";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import PorterchainWordmark from "@/components/brand/PorterchainWordmark";
import GuestTrackLookup from "@/components/portal/GuestTrackLookup";
import LoginBrandPanel from "@/components/portal/LoginBrandPanel";
import { porterchainClerkAppearance } from "@/lib/clerk-appearance";

export default function UnifiedSignIn({ redirectUrl = "/login" }: { redirectUrl?: string }) {
  const t = useTranslations("login");

  return (
    <div className="min-h-[calc(100dvh-var(--nav-height))] grid lg:grid-cols-2 bg-gray-bg">
      <LoginBrandPanel />

      <div className="flex flex-col justify-center px-4 py-8 sm:px-6 sm:py-10 md:px-8 lg:px-12 xl:px-14">
        <div className="w-full max-w-md mx-auto min-w-0">
          <div className="mb-8 lg:hidden flex flex-col items-center text-center">
            <PorterchainWordmark tone="light" size="lg" />
            <p className="mt-4 text-sm text-muted max-w-xs">{t("subtitle")}</p>
          </div>

          <div className="rounded-2xl border border-primary/8 bg-white p-5 sm:p-6 md:p-8 shadow-premium">
            <div className="mb-6">
              <h2 className="text-xl font-semibold tracking-tight text-primary">{t("title")}</h2>
              <p className="mt-1.5 text-sm text-muted">{t("roleNote")}</p>
            </div>

            <SignIn
              routing="hash"
              forceRedirectUrl={redirectUrl}
              signUpForceRedirectUrl={redirectUrl}
              fallbackRedirectUrl={redirectUrl}
              appearance={porterchainClerkAppearance}
            />
          </div>

          <div className="mt-6">
            <GuestTrackLookup compact variant="login" />
          </div>

          <p className="mt-8 text-center text-sm text-muted">
            {t("needHelp")}{" "}
            <Link href="/contact" className="font-medium text-secondary hover:text-[#1d4ed8]">
              {t("needHelpLink")}
            </Link>
          </p>

          <p className="mt-3 text-center">
            <Link href="/" className="text-xs text-muted hover:text-primary transition-colors">
              {t("backHome")}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
