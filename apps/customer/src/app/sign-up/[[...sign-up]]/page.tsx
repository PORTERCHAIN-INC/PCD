"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@porterchain/auth/oidc/client";
import { signUpUnavailableCopy, KeycloakSignInPanel } from "@porterchain/auth";
import { isDevelopmentBuild } from "@porterchain/auth/devBypass";
import { CustomerAuthLoading, CustomerAuthScreen } from "@/components/auth/CustomerAuthScreen";
import { isAuthConfigured } from "@/lib/env";

export default function SignUpPage() {
  if (!isAuthConfigured()) {
    return <AuthUnavailable />;
  }
  return <SignUpWithAuth />;
}

function AuthUnavailable() {
  if (!isDevelopmentBuild()) {
    return (
      <CustomerAuthScreen
        mode="sign-up"
        title={signUpUnavailableCopy.title}
        subtitle={signUpUnavailableCopy.subtitle}
      >
        <div className="space-y-4">
          <p className="text-sm leading-relaxed text-muted">{signUpUnavailableCopy.body}</p>
          <Link
            href="/sign-in"
            className="flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#1d4ed8]"
          >
            Back to sign in
          </Link>
        </div>
      </CustomerAuthScreen>
    );
  }
  return (
    <CustomerAuthScreen
      mode="sign-up"
      title="Local development"
      subtitle="Keycloak is not configured for this environment."
    >
      <div className="space-y-4">
        <p className="text-sm leading-relaxed text-muted">
          Set NEXT_PUBLIC_KEYCLOAK_CLIENT_ID, KEYCLOAK_URL and AUTH_SESSION_SECRET (see
          .env.example), then refresh.
        </p>
        <Link
          href="/sign-in"
          className="flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#1d4ed8]"
        >
          Back to sign in
        </Link>
      </div>
    </CustomerAuthScreen>
  );
}

function SignUpWithAuth() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      router.replace("/send");
    }
  }, [isLoaded, isSignedIn, router]);

  if (!isLoaded || isSignedIn) {
    return <CustomerAuthLoading label="Opening onboarding…" />;
  }

  return (
    <CustomerAuthScreen
      mode="sign-up"
      title="Create your account"
      subtitle="Track deliveries, invoices, and support in one place."
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
    </CustomerAuthScreen>
  );
}
