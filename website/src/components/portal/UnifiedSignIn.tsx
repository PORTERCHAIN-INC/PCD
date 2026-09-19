"use client";

import { SignIn } from "@clerk/nextjs";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { porterchainClerkAppearance } from "@porterchain/auth";
import PlatformAuthLayout from "@/components/portal/PlatformAuthLayout";
import { adminSignInUrl, driverSignInUrl } from "@/data/portal-links";

type UnifiedSignInProps = {
  /** Absolute path Clerk should open after auth (e.g. /en/login/continue). */
  redirectUrl: string;
};

/**
 * Platform Clerk SignIn for retail (customer + merchant).
 * Open SignUp is on /sign-up. Admin and Driver use separate portal URLs.
 */
export default function UnifiedSignIn({ redirectUrl }: UnifiedSignInProps) {
  const t = useTranslations("login");
  const locale = useLocale();
  const signInPath = `/${locale}/login`;
  const signUpPath = `/${locale}/sign-up`;

  return (
    <PlatformAuthLayout
      mode="sign-in"
      title={t("title")}
      subtitle={t("subtitle")}
      footer={
        <div className="space-y-4">
          <p>
            {t("needHelp")}{" "}
            <Link
              href="/sign-up"
              className="font-semibold text-secondary underline-offset-2 hover:text-[#1d4ed8] hover:underline"
            >
              {t("needHelpLink")}
            </Link>
          </p>
          <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-xs text-muted sm:justify-start">
            <a href={adminSignInUrl} className="transition-colors hover:text-primary">
              {t("staffSignIn")}
            </a>
            <span className="text-primary/20" aria-hidden>
              ·
            </span>
            <a href={driverSignInUrl} className="transition-colors hover:text-primary">
              {t("driverSignIn")}
            </a>
          </div>
        </div>
      }
    >
      <SignIn
        routing="path"
        path={signInPath}
        signUpUrl={signUpPath}
        forceRedirectUrl={redirectUrl}
        signUpForceRedirectUrl={redirectUrl}
        fallbackRedirectUrl={redirectUrl}
        appearance={porterchainClerkAppearance}
      />
    </PlatformAuthLayout>
  );
}
