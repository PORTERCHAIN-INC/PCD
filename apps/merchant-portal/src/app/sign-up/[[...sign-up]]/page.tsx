"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@porterchain/auth/oidc/client";
import { useEffect } from "react";
import {
  AuthLoadFailed,
  signUpUnavailableCopy,
  useAuthLoadTimeout,
  KeycloakSignInPanel,
} from "@porterchain/auth";
import { isDevelopmentBuild } from "@porterchain/auth/devBypass";
import { MerchantAuthLoading, MerchantAuthScreen } from "@/components/auth/MerchantAuthScreen";
import { isAuthConfigured } from "@/lib/env";

function AuthUnavailable() {
  if (!isDevelopmentBuild()) {
    return (
      <MerchantAuthScreen
        mode="sign-up"
        title={signUpUnavailableCopy.title}
        subtitle={signUpUnavailableCopy.subtitle}
      >
        <div className="space-y-4">
          <p className="text-sm leading-relaxed text-muted">{signUpUnavailableCopy.body}</p>
          <Link
            href="/sign-in"
            className="inline-flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#1d4ed8]"
          >
            Back to sign in
          </Link>
        </div>
      </MerchantAuthScreen>
    );
  }
  return (
    <MerchantAuthScreen
      mode="sign-up"
      title="Local development"
      subtitle="Keycloak is not configured. Merchant sign-up needs Platform Keycloak keys."
    >
      <div className="space-y-4">
        <p className="text-sm leading-relaxed text-muted">
          Set NEXT_PUBLIC_KEYCLOAK_CLIENT_ID, KEYCLOAK_URL and AUTH_SESSION_SECRET (see
          .env.example), then refresh.
        </p>
        <Link
          href="/sign-in"
          className="inline-flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#1d4ed8]"
        >
          Back to sign in
        </Link>
      </div>
    </MerchantAuthScreen>
  );
}

function SignUpWithAuth() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();
  const loadTimedOut = useAuthLoadTimeout(isLoaded);

  // Already signed in: go to the dashboard and let the gate decide onboarding vs portal.
  useEffect(() => {
    if (isLoaded && isSignedIn) {
      router.replace("/dashboard");
    }
  }, [isLoaded, isSignedIn, router]);

  if (loadTimedOut) {
    return <AuthLoadFailed title="Sign-up could not load" />;
  }
  if (!isLoaded || isSignedIn) {
    return <MerchantAuthLoading label="Opening your portal…" />;
  }

  return (
    <MerchantAuthScreen
      mode="sign-up"
      title="Start with PorterChain"
      subtitle="Create your Keycloak account (password stays here). Then fill the company file. Teammates use this same sign-up URL with the email your owner reserved."
      footer={
        <>
          Already have an account?{" "}
          <Link
            href="/sign-in"
            className="font-semibold text-secondary underline-offset-2 hover:underline"
          >
            Sign in
          </Link>
        </>
      }
    >
      <KeycloakSignInPanel mode="sign-up" returnTo={"/"} />
    </MerchantAuthScreen>
  );
}

export default function SignUpPage() {
  if (!isAuthConfigured()) {
    return <AuthUnavailable />;
  }
  return <SignUpWithAuth />;
}
