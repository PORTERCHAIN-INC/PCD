"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { SignUp, useAuth } from "@clerk/nextjs";
import { useEffect } from "react";
import { PasswordRequirements, porterchainClerkAppearance } from "@porterchain/auth";
import { MerchantAuthLoading, MerchantAuthScreen } from "@/components/auth/MerchantAuthScreen";
import { isClerkConfigured } from "@/lib/env";

function ClerkUnavailable() {
  return (
    <MerchantAuthScreen
      mode="sign-up"
      title="Invitation required"
      subtitle="Configure Clerk to enable merchant sign-up locally."
    >
      <div className="space-y-4">
        <p className="text-sm leading-relaxed text-muted">
          Merchant accounts need Clerk configured for Google or Microsoft sign-up in local
          development.
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

function SignUpWithClerk() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      router.replace("/onboarding");
    }
  }, [isLoaded, isSignedIn, router]);

  if (!isLoaded || isSignedIn) {
    return <MerchantAuthLoading label="Opening onboarding…" />;
  }

  return (
    <MerchantAuthScreen
      mode="sign-up"
      title="Start with Porterchain"
      subtitle="Use your work Google or Microsoft account. Your organization completes onboarding after sign-up."
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
      <SignUp
        routing="path"
        path="/sign-up"
        signInUrl="/sign-in"
        forceRedirectUrl="/onboarding"
        fallbackRedirectUrl="/onboarding"
        appearance={porterchainClerkAppearance}
      />
      <PasswordRequirements />
    </MerchantAuthScreen>
  );
}

export default function SignUpPage() {
  if (!isClerkConfigured()) {
    return <ClerkUnavailable />;
  }
  return <SignUpWithClerk />;
}
