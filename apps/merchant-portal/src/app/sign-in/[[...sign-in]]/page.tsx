"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { SignIn, useAuth } from "@clerk/nextjs";
import { isClerkConfigured, publicEnv } from "@/lib/env";
import { porterchainClerkAppearance } from "@/lib/clerk-appearance";
import { platformLoginUrl } from "@porterchain/auth";

function ClerkUnavailable() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-bg p-4">
      <div className="w-full max-w-md rounded-2xl border border-primary/10 portal-surface p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-primary">Porterchain Merchant Portal</h1>
        <p className="mt-2 text-sm text-muted">
          Clerk is not configured for local development, so the sign-in widget cannot load.
        </p>
        <Link
          href="/dashboard"
          className="mt-6 flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white hover:bg-[#1d4ed8]"
        >
          Continue in dev mode (no auth)
        </Link>
      </div>
    </div>
  );
}

function SignInWithClerk() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      setChecking(false);
      return;
    }
    router.replace("/onboarding");
  }, [isLoaded, isSignedIn, router]);

  if (!isLoaded || checking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-bg">
        <p className="text-sm text-muted">Loading…</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-bg p-4">
      <div className="mb-6 max-w-md text-center">
        <h1 className="text-2xl font-bold text-primary">Porterchain Merchant Portal</h1>
        <p className="mt-2 text-sm text-muted">
          Sign in with your approved business account. Prefer Platform login at{" "}
          <a href={platformLoginUrl(publicEnv.websiteUrl)} className="font-semibold text-secondary">
            {platformLoginUrl(publicEnv.websiteUrl)}
          </a>
          .
        </p>
      </div>
      <SignIn
        routing="path"
        path="/sign-in"
        forceRedirectUrl="/onboarding"
        fallbackRedirectUrl="/onboarding"
        appearance={porterchainClerkAppearance}
      />
      <p className="mt-6 max-w-sm text-center text-xs text-muted">
        Merchant access is invitation-only. Contact your Porterchain account manager if you need an
        invite.
      </p>
    </div>
  );
}

export default function SignInPage() {
  if (!isClerkConfigured()) {
    return <ClerkUnavailable />;
  }
  return <SignInWithClerk />;
}
