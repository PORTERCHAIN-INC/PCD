"use client";

/**
 * Keycloak open sign-up (pc-website) for retail (customer + merchant).
 * After success → /login/continue for portal routing.
 */

import { Suspense, useEffect, useState } from "react";
import { useAuth } from "@porterchain/auth/oidc/client";
import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { Link } from "@/i18n/navigation";
import {
  AuthLoadFailed,
  KeycloakSignInPanel,
  useAuthLoadTimeout,
  isDevelopmentBuild,
} from "@porterchain/auth";
import LoginShell from "@/components/portal/LoginShell";
import PlatformAuthLayout, { PlatformAuthLoading } from "@/components/portal/PlatformAuthLayout";
import PostAuthPortalRedirect from "@/components/portal/PostAuthPortalRedirect";
import { isAuthConfigured } from "@/lib/env";
import { readQuoteIntent, rememberQuoteIntent } from "@/lib/visitor-tracking";

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
  const searchParams = useSearchParams();
  const { isLoaded, isSignedIn } = useAuth();
  const loadTimedOut = useAuthLoadTimeout(isLoaded);

  const intent = searchParams.get("intent") ?? undefined;
  // Internal links no longer carry ?from= (canonical URLs); the clicked CTA is in sessionStorage.
  const [storedFrom, setStoredFrom] = useState<string | undefined>(undefined);
  useEffect(() => {
    setStoredFrom(readQuoteIntent().from);
  }, []);
  const from = searchParams.get("from") ?? storedFrom;
  const vehicle = searchParams.get("vehicle") ?? undefined;
  const ref = searchParams.get("ref") ?? undefined;

  useEffect(() => {
    if (intent || from || vehicle || ref) {
      rememberQuoteIntent({ intent, from, vehicle, ref });
    }
  }, [intent, from, vehicle, ref]);

  const continueParams = new URLSearchParams();
  if (intent) continueParams.set("intent", intent);
  if (from) continueParams.set("from", from);
  if (vehicle) continueParams.set("vehicle", vehicle);
  if (ref) continueParams.set("ref", ref);
  const continueQs = continueParams.toString();
  const continuePath = continueQs
    ? `/${locale}/login/continue?${continueQs}`
    : `/${locale}/login/continue`;

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    if (typeof window === "undefined") return;
    if (window.location.pathname.includes("/login/continue")) return;
    window.location.replace(continuePath);
  }, [isLoaded, isSignedIn, continuePath]);

  if (!isAuthConfigured()) {
    const dev = isDevelopmentBuild();
    return (
      <LoginShell>
        <PlatformAuthLayout
          mode="sign-up"
          title={dev ? t("signUpTitle") : t("signUpUnavailableTitle")}
          subtitle={dev ? t("devSetupNote") : t("unavailableBody")}
        >
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

  if (loadTimedOut) return <AuthLoadFailed title="Sign-up could not load" />;
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
        <KeycloakSignInPanel
          mode="sign-up"
          returnTo={continuePath}
          primaryLabel={t("signUpTitle")}
        />
      </PlatformAuthLayout>
    </LoginShell>
  );
}
