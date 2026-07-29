"use client";

/**
 * Website `/login` — Clerk SignIn only when signed out.
 * Signed-in users never see #/factor-one; they go to /login/continue → module.
 */

import { Suspense, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import LoginShell from "@/components/portal/LoginShell";
import LoginStatusCard from "@/components/portal/LoginStatusCard";
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
      <div className="min-h-[calc(100dvh-var(--nav-height))] flex items-center justify-center px-5 py-10 bg-gray-bg">
        <LoginStatusCard title={t("title")} loading />
      </div>
    </LoginShell>
  );
}

function LoginContent() {
  const t = useTranslations("login");
  const locale = useLocale();
  const { isLoaded, isSignedIn } = useAuth();
  const continuePath = `/${locale}/login/continue`;

  // Already signed in on /login or /login#/factor-one → leave SignIn immediately
  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    if (typeof window === "undefined") return;
    if (window.location.pathname.includes("/login/continue")) return;
    window.location.replace(continuePath);
  }, [isLoaded, isSignedIn, continuePath]);

  if (!isClerkConfigured()) {
    return (
      <LoginShell>
        <div className="min-h-[calc(100dvh-var(--nav-height))] flex items-center justify-center px-5 py-12 bg-gray-bg">
          <LoginStatusCard title={t("title")} description={t("devModeNote")}>
            <Link
              href="/"
              className="inline-flex justify-center rounded-xl bg-secondary px-5 py-3 text-white font-semibold text-sm hover:bg-[#1d4ed8] transition-colors"
            >
              {t("backHome")}
            </Link>
          </LoginStatusCard>
        </div>
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
