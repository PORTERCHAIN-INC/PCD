"use client";

/**
 * Platform Clerk open SignUp for retail (customer + merchant).
 * After success → /login/continue for portal routing.
 */

import { Suspense, useEffect } from "react";
import { SignUp, useAuth } from "@clerk/nextjs";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { porterchainClerkAppearance } from "@porterchain/auth";
import LoginShell from "@/components/portal/LoginShell";
import PlatformAuthLayout, { PlatformAuthLoading } from "@/components/portal/PlatformAuthLayout";
import PostAuthPortalRedirect from "@/components/portal/PostAuthPortalRedirect";
import { isClerkConfigured } from "@/lib/env";

export default function SignUpPage() {
  return (
    <Suspense fallback={<SignUpFallback />}>
      <SignUpContent />
    </Suspense>
  );
}

function SignUpFallback() {
  const t = useTranslations("login");
  return (
    <LoginShell>
      <PlatformAuthLoading title={t("signUpTitle")} label={t("redirecting")} />
    </LoginShell>
  );
}

function SignUpContent() {
  const t = useTranslations("login");
  const locale = useLocale();
  const { isLoaded, isSignedIn } = useAuth();
  const continuePath = `/${locale}/login/continue`;
  const signUpPath = `/${locale}/sign-up`;
  const signInPath = `/${locale}/login`;

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    if (typeof window === "undefined") return;
    if (window.location.pathname.includes("/login/continue")) return;
    window.location.replace(continuePath);
  }, [isLoaded, isSignedIn, continuePath]);

  if (!isClerkConfigured()) {
    return (
      <LoginShell>
        <PlatformAuthLayout mode="sign-up" title={t("signUpTitle")} subtitle={t("devModeNote")}>
          <Link
            href="/"
            className="inline-flex w-full justify-center rounded-xl bg-secondary px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#1d4ed8]"
          >
            {t("backHome")}
          </Link>
        </PlatformAuthLayout>
      </LoginShell>
    );
  }

  if (!isLoaded) return <SignUpFallback />;
  if (isSignedIn) return <PostAuthPortalRedirect />;

  return (
    <LoginShell>
      <PlatformAuthLayout
        mode="sign-up"
        title={t("signUpTitle")}
        subtitle={t("signUpSubtitle")}
        footer={
          <>
            {t("haveAccount")}{" "}
            <Link
              href="/login"
              className="font-semibold text-secondary underline-offset-2 hover:text-[#1d4ed8] hover:underline"
            >
              {t("title")}
            </Link>
          </>
        }
      >
        <SignUp
          routing="path"
          path={signUpPath}
          signInUrl={signInPath}
          forceRedirectUrl={continuePath}
          fallbackRedirectUrl={continuePath}
          appearance={porterchainClerkAppearance}
        />
      </PlatformAuthLayout>
    </LoginShell>
  );
}
