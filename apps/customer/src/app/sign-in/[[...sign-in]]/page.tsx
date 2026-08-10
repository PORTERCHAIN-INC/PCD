"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { SignIn, useAuth } from "@clerk/nextjs";
import { porterchainClerkAppearance, safeAppRedirect } from "@porterchain/auth";
import { CustomerAuthLoading, CustomerAuthScreen } from "@/components/auth/CustomerAuthScreen";
import { isClerkConfigured, publicEnv } from "@/lib/env";

export default function SignInPage() {
  return (
    <Suspense fallback={<CustomerAuthLoading label="Preparing sign-in…" />}>
      <SignInGate />
    </Suspense>
  );
}

function SignInGate() {
  if (!isClerkConfigured()) {
    return (
      <CustomerAuthScreen
        title="Local development"
        subtitle="Clerk is not configured for this environment."
      >
        <div className="space-y-4">
          <p className="text-sm leading-relaxed text-muted">
            Add Platform Clerk keys via <code className="text-primary">pnpm clerk:sync</code>, then
            refresh.
          </p>
          <Link
            href="/dashboard"
            className="flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#1d4ed8]"
          >
            Continue in dev mode
          </Link>
        </div>
      </CustomerAuthScreen>
    );
  }
  return <SignInContent />;
}

function SignInContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isLoaded, isSignedIn } = useAuth();
  const redirectUrl = safeAppRedirect(searchParams.get("redirect_url"), {
    fallback: "/onboarding",
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
      showPlatformLogin
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
      <SignIn
        routing="path"
        path="/sign-in"
        signUpUrl="/sign-up"
        forceRedirectUrl={redirectUrl}
        fallbackRedirectUrl={redirectUrl}
        appearance={porterchainClerkAppearance}
      />
    </CustomerAuthScreen>
  );
}
