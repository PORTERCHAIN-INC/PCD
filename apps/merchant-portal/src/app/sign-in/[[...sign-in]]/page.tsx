"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { SignIn, useAuth } from "@clerk/nextjs";
import { porterchainClerkAppearance, safeAppRedirect } from "@porterchain/auth";
import { MerchantAuthLoading, MerchantAuthScreen } from "@/components/auth/MerchantAuthScreen";
import { isClerkConfigured } from "@/lib/env";

function ClerkUnavailable() {
  return (
    <MerchantAuthScreen
      title="Local development"
      subtitle="Clerk is not configured for this environment. The sign-in widget cannot load without keys."
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
    </MerchantAuthScreen>
  );
}

function SignInWithClerk() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isLoaded, isSignedIn } = useAuth();
  const [checking, setChecking] = useState(true);
  const redirectUrl = safeAppRedirect(searchParams.get("redirect_url"), {
    fallback: "/onboarding",
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

  if (!isLoaded || checking) {
    return <MerchantAuthLoading label="Preparing sign-in…" />;
  }

  return (
    <MerchantAuthScreen
      title="Business sign-in"
      subtitle="Access capacity, shipments, and billing for your organization."
      showPlatformLogin
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
      <SignIn
        routing="path"
        path="/sign-in"
        signUpUrl="/sign-up"
        forceRedirectUrl={redirectUrl}
        fallbackRedirectUrl={redirectUrl}
        appearance={porterchainClerkAppearance}
      />
    </MerchantAuthScreen>
  );
}

export default function SignInPage() {
  if (!isClerkConfigured()) {
    return <ClerkUnavailable />;
  }
  return (
    <Suspense fallback={<MerchantAuthLoading label="Preparing sign-in…" />}>
      <SignInWithClerk />
    </Suspense>
  );
}
