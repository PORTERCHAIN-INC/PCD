"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@porterchain/auth/oidc/client";
import { safeAppRedirect, signInUnavailableCopy, KeycloakSignInPanel } from "@porterchain/auth";
import { isDevelopmentBuild } from "@porterchain/auth/devBypass";
import { CustomerAuthLoading, CustomerAuthScreen } from "@/components/auth/CustomerAuthScreen";
import { isAuthConfigured, publicEnv } from "@/lib/env";

export default function SignInPage() {
  return (
    <Suspense fallback={<CustomerAuthLoading label="Preparing sign-in…" />}>
      <SignInGate />
    </Suspense>
  );
}

function SignInGate() {
  if (!isAuthConfigured()) {
    return <AuthUnavailable />;
  }
  return <SignInContent />;
}

function AuthUnavailable() {
  if (!isDevelopmentBuild()) {
    return (
      <CustomerAuthScreen
        title={signInUnavailableCopy.title}
        subtitle={signInUnavailableCopy.subtitle}
      >
        <p className="text-sm leading-relaxed text-muted">{signInUnavailableCopy.body}</p>
      </CustomerAuthScreen>
    );
  }
  return (
    <CustomerAuthScreen
      title="Local development"
      subtitle="Keycloak is not configured for this environment."
    >
      <div className="space-y-4">
        <p className="text-sm leading-relaxed text-muted">
          Set NEXT_PUBLIC_KEYCLOAK_CLIENT_ID, KEYCLOAK_URL and AUTH_SESSION_SECRET (see
          .env.example), then refresh.
        </p>
        <Link
          href="/orders"
          className="flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#1d4ed8]"
        >
          Continue
        </Link>
      </div>
    </CustomerAuthScreen>
  );
}

function SignInContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isLoaded, isSignedIn } = useAuth();
  const redirectUrl = safeAppRedirect(searchParams.get("redirect_url"), {
    fallback: "/send",
    blockPrefixes: ["/sign-in", "/sign-up"],
  });
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      setChecking(false);
      return;
    }
    router.replace(redirectUrl);
  }, [isLoaded, isSignedIn, redirectUrl, router]);

  if (!isLoaded || checking) {
    return <CustomerAuthLoading label="Preparing sign-in…" />;
  }

  return (
    <CustomerAuthScreen
      title="Customer sign-in"
      subtitle="View deliveries, invoices, and support for your shipments."
      footer={
        <>
          New here?{" "}
          <Link
            href="/sign-up"
            className="font-semibold text-secondary underline-offset-2 hover:underline"
          >
            Create an account
          </Link>
          . Tracking one shipment without an account?{" "}
          <a
            href={`${publicEnv.websiteUrl}/track`}
            className="font-semibold text-secondary underline-offset-2 hover:underline"
          >
            Use guest tracking
          </a>
          .
        </>
      }
    >
      <KeycloakSignInPanel mode="sign-in" returnTo={redirectUrl} />
    </CustomerAuthScreen>
  );
}
