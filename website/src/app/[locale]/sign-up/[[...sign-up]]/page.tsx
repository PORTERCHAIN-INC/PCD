"use client";

/**
 * Platform Clerk open SignUp for retail (customer + merchant).
 * After success → /login/continue for portal routing.
 */

import { Suspense, useEffect, useState } from "react";
import { SignUp, useAuth } from "@clerk/nextjs";
import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { Link } from "@/i18n/navigation";
import {
  PasswordRequirements,
  isDevelopmentBuild,
  porterchainClerkAppearance,
} from "@porterchain/auth";
import LoginShell from "@/components/portal/LoginShell";
import PlatformAuthLayout, { PlatformAuthLoading } from "@/components/portal/PlatformAuthLayout";
import PostAuthPortalRedirect from "@/components/portal/PostAuthPortalRedirect";
import { isClerkConfigured } from "@/lib/env";
import { getStoredAttribution } from "@/lib/seo/attribution";
import { getOrCreateVisitorId, rememberQuoteIntent } from "@/lib/visitor-tracking";

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

  const intent = searchParams.get("intent") ?? undefined;
  const from = searchParams.get("from") ?? undefined;
  const vehicle = searchParams.get("vehicle") ?? undefined;
  const ref = searchParams.get("ref") ?? undefined;

  useEffect(() => {
    if (intent || from || vehicle || ref) {
      rememberQuoteIntent({ intent, from, vehicle, ref });
    }
  }, [intent, from, vehicle, ref]);

  // Session UTM / landing attribution travels with the new account (Clerk unsafeMetadata).
  const [signupAttribution, setSignupAttribution] = useState<Record<string, string>>({});
  useEffect(() => {
    const att = getStoredAttribution();
    const picked: Record<string, string | undefined> = {
      utm_source: att.utm_source,
      utm_medium: att.utm_medium,
      utm_campaign: att.utm_campaign,
      utm_term: att.utm_term,
      utm_content: att.utm_content,
      from: from ?? att.from,
      landing_page: att.landingPageUrl,
      referrer: att.referrer,
      pc_vid: getOrCreateVisitorId(),
    };
    setSignupAttribution(
      Object.fromEntries(Object.entries(picked).filter(([, v]) => Boolean(v))) as Record<
        string,
        string
      >
    );
  }, [from]);

  const continueParams = new URLSearchParams();
  if (intent) continueParams.set("intent", intent);
  if (from) continueParams.set("from", from);
  if (vehicle) continueParams.set("vehicle", vehicle);
  if (ref) continueParams.set("ref", ref);
  const continueQs = continueParams.toString();
  const continuePath = continueQs
    ? `/${locale}/login/continue?${continueQs}`
    : `/${locale}/login/continue`;
  const signUpPath = `/${locale}/sign-up`;
  const signInPath = `/${locale}/login`;

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    if (typeof window === "undefined") return;
    if (window.location.pathname.includes("/login/continue")) return;
    window.location.replace(continuePath);
  }, [isLoaded, isSignedIn, continuePath]);

  if (!isClerkConfigured()) {
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
          unsafeMetadata={{ signup_attribution: signupAttribution }}
        />
        <PasswordRequirements
          copy={{
            title: t("passwordTitle"),
            intro: t("passwordIntro"),
            minLength: t("passwordMinLength"),
            uppercase: t("passwordUppercase"),
            lowercase: t("passwordLowercase"),
            number: t("passwordNumber"),
            special: t("passwordSpecial"),
            allowedLabel: t("passwordAllowedLabel"),
            strength: t("passwordStrength"),
          }}
        />
      </PlatformAuthLayout>
    </LoginShell>
  );
}
