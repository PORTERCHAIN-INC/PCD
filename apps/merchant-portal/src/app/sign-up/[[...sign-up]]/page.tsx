"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { SignUp, useAuth } from "@clerk/nextjs";
import { useEffect } from "react";
import { isClerkConfigured } from "@/lib/env";
import { porterchainClerkAppearance } from "@/lib/clerk-appearance";

function ClerkUnavailable() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-bg p-4">
      <div className="w-full max-w-md rounded-2xl border border-primary/10 bg-white p-8 shadow-sm text-center">
        <h1 className="text-2xl font-bold text-primary">Invitation required</h1>
        <p className="mt-3 text-sm text-muted leading-relaxed">
          Merchant accounts are invite-only. Configure Clerk to enable Google or Microsoft sign-up
          in local development.
        </p>
        <Link
          href="/sign-in"
          className="mt-8 inline-flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white hover:bg-[#1d4ed8]"
        >
          Back to sign in
        </Link>
      </div>
    </div>
  );
}

function SignUpWithClerk() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      router.replace("/onboarding");
    }
  }, [isLoaded, isSignedIn, router]);

  if (!isLoaded || isSignedIn) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-bg">
        <p className="text-sm text-muted">Loading…</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-bg p-4">
      <div className="mb-6 max-w-md text-center">
        <h1 className="text-2xl font-bold text-primary">Start with Porterchain</h1>
        <p className="mt-2 text-sm text-muted">
          Use your work Google or Microsoft account. Your organization must be provisioned after
          sign-up.
        </p>
      </div>
      <SignUp
        routing="path"
        path="/sign-up"
        forceRedirectUrl="/onboarding"
        fallbackRedirectUrl="/onboarding"
        appearance={porterchainClerkAppearance}
      />
      <p className="mt-6 max-w-sm text-center text-xs text-muted">
        Already invited?{" "}
        <Link href="/sign-in" className="font-medium text-secondary hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}

export default function SignUpPage() {
  if (!isClerkConfigured()) {
    return <ClerkUnavailable />;
  }
  return <SignUpWithClerk />;
}
