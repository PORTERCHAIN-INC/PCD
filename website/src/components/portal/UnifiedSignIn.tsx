"use client";

import { SignIn } from "@clerk/nextjs";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import PorterchainWordmark from "@/components/brand/PorterchainWordmark";
import { porterchainClerkAppearance } from "@/lib/clerk-appearance";

type UnifiedSignInProps = {
  /** Absolute path Clerk should open after auth (e.g. /en/login/continue). */
  redirectUrl: string;
};

/**
 * Platform Clerk sign-in for signed-out users only.
 * After success Clerk goes to redirectUrl — never leave the user on #/factor-one.
 *
 * path routing must match the real browser path (`/{locale}/login`), not bare `/login`.
 */
export default function UnifiedSignIn({ redirectUrl }: UnifiedSignInProps) {
  const t = useTranslations("login");
  const locale = useLocale();
  const signInPath = `/${locale}/login`;

  return (
    <div className="min-h-[calc(100dvh-var(--nav-height))] flex flex-col items-center justify-center bg-gray-bg px-4 py-10 sm:px-6">
      <div className="mb-8 flex flex-col items-center text-center">
        <PorterchainWordmark tone="light" size="lg" />
        <h1 className="mt-6 text-xl font-semibold tracking-tight text-primary sm:text-2xl">
          {t("title")}
        </h1>
        <p className="mt-2 max-w-sm text-sm text-muted">{t("subtitle")}</p>
      </div>

      <div className="w-full max-w-md min-w-0 rounded-2xl border border-primary/8 bg-white p-5 sm:p-6 md:p-8 shadow-premium">
        <SignIn
          routing="path"
          path={signInPath}
          forceRedirectUrl={redirectUrl}
          signUpForceRedirectUrl={redirectUrl}
          fallbackRedirectUrl={redirectUrl}
          appearance={porterchainClerkAppearance}
        />
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
  );
}
