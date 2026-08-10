"use client";

/**
 * Website `/login` (+ Clerk path steps under optional catch-all).
 * Signed-in users go to /login/continue → portal picker / module home.
 */

import { Suspense, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import LoginShell from "@/components/portal/LoginShell";
import PlatformAuthLayout, { PlatformAuthLoading } from "@/components/portal/PlatformAuthLayout";
import PostAuthPortalRedirect from "@/components/portal/PostAuthPortalRedirect";
import UnifiedSignIn from "@/components/portal/UnifiedSignIn";
import { isClerkConfigured } from "@/lib/env";

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginPageFallback />}>
      <LoginContent />
    </Suspense>
  );
}

function LoginPageFallback() {
  const t = useTranslations("login");
  return (
    <LoginShell>
      <PlatformAuthLoading title={t("title")} label={t("redirecting")} />
    </LoginShell>
  );
}

function LoginContent() {
  const t = useTranslations("login");
  const locale = useLocale();
  const { isLoaded, isSignedIn } = useAuth();
  const continuePath = `/${locale}/login/continue`;

  // Already signed in on /login or /login/<clerk-step> → continue immediately
  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    if (typeof window === "undefined") return;
    if (window.location.pathname.includes("/login/continue")) return;
    window.location.replace(continuePath);
  }, [isLoaded, isSignedIn, continuePath]);

  if (!isClerkConfigured()) {
    return (
      <LoginShell>
        <PlatformAuthLayout title={t("title")} subtitle={t("devModeNote")}>
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

  if (!isLoaded) {
    return <LoginPageFallback />;
  }

  if (isSignedIn) {
    return <PostAuthPortalRedirect />;
  }

  return (
    <LoginShell>
      <UnifiedSignIn redirectUrl={continuePath} />
    </LoginShell>
  );
}
