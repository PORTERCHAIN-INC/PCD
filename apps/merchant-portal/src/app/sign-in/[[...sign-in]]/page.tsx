"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@porterchain/auth/oidc/client";
import {
  AuthLoadFailed,
  safeAppRedirect,
  useAuthLoadTimeout,
  signInUnavailableCopy,
  KeycloakSignInPanel,
} from "@porterchain/auth";
import { isDevelopmentBuild } from "@porterchain/auth/devBypass";
import { MerchantAuthLoading, MerchantAuthScreen } from "@/components/auth/MerchantAuthScreen";
import { isAuthConfigured, useLocalDevAuth } from "@/lib/env";

function LocalDevSignIn() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = safeAppRedirect(searchParams.get("redirect_url"), {
    fallback: "/dashboard",
    blockPrefixes: ["/sign-in", "/sign-up", "/onboarding"],
  });

  useEffect(() => {
    router.replace(redirectUrl);
  }, [redirectUrl, router]);

  return (
    <MerchantAuthScreen
      title="Local development"
      subtitle="Clerk is off on localhost. You continue as the local merchant account."
    >
      <Link
        href={redirectUrl}
        className="flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#1d4ed8]"
      >
        Continue
      </Link>
    </MerchantAuthScreen>
  );
}

/** Missing Clerk keys. A shipped build gets no dev-mode door and no internal instructions (BJ). */
function AuthUnavailable() {
  if (!isDevelopmentBuild()) {
    return (
      <MerchantAuthScreen
        title={signInUnavailableCopy.title}
        subtitle={signInUnavailableCopy.subtitle}
      >
        <p className="text-sm leading-relaxed text-muted">{signInUnavailableCopy.body}</p>
      </MerchantAuthScreen>
    );
  }
  return (
    <MerchantAuthScreen
      title="Local development"
      subtitle="Keycloak is not configured for this environment. The sign-in widget cannot load without keys."
    >
      <div className="space-y-4">
        <p className="text-sm leading-relaxed text-muted">
          Set NEXT_PUBLIC_KEYCLOAK_CLIENT_ID, KEYCLOAK_URL and AUTH_SESSION_SECRET (see
          .env.example), then refresh.
        </p>
        <Link
          href="/dashboard"
          className="flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#1d4ed8]"
        >
          Continue
        </Link>
      </div>
    </MerchantAuthScreen>
  );
}

function SignInWithAuth() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isLoaded, isSignedIn } = useAuth();
  const [checking, setChecking] = useState(true);
  const loadTimedOut = useAuthLoadTimeout(isLoaded);
  // Land on the dashboard; MerchantAccessGate sends seats that are not ready to /onboarding.
  const redirectUrl = safeAppRedirect(searchParams.get("redirect_url"), {
    fallback: "/dashboard",
    blockPrefixes: ["/sign-in", "/sign-up"],
  });

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      setChecking(false);
      return;
    }
    router.replace(redirectUrl);
  }, [isLoaded, isSignedIn, redirectUrl, router]);

  if (loadTimedOut) {
    return <AuthLoadFailed />;
  }
  if (!isLoaded || checking) {
    return <MerchantAuthLoading label="Preparing sign-in…" />;
  }

  return (
    <MerchantAuthScreen
      title="Business sign-in"
      subtitle="Access capacity, shipments, and billing for your organization."
      footer={
        <>
          New organization?{" "}
          <Link
            href="/sign-up"
            className="font-semibold text-secondary underline-offset-2 hover:underline"
          >
            Create an account
          </Link>
          . Existing merchants may also be invited by Porterchain ops.
        </>
      }
    >
      <KeycloakSignInPanel mode="sign-in" returnTo={redirectUrl} />
    </MerchantAuthScreen>
  );
}

export default function SignInPage() {
  if (useLocalDevAuth()) {
    return (
      <Suspense fallback={<MerchantAuthLoading label="Opening local session…" />}>
        <LocalDevSignIn />
      </Suspense>
    );
  }
  if (!isAuthConfigured()) {
    return <AuthUnavailable />;
  }
  return (
    <Suspense fallback={<MerchantAuthLoading label="Preparing sign-in…" />}>
      <SignInWithAuth />
    </Suspense>
  );
}
