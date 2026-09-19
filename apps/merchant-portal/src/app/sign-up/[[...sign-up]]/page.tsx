"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { SignUp, useAuth } from "@clerk/nextjs";
import { useEffect } from "react";
import {
  PasswordRequirements,
  porterchainClerkAppearance,
  signUpUnavailableCopy,
} from "@porterchain/auth";
import { isDevelopmentBuild } from "@porterchain/auth/devBypass";
import { MerchantAuthLoading, MerchantAuthScreen } from "@/components/auth/MerchantAuthScreen";
import { isClerkConfigured } from "@/lib/env";

function ClerkUnavailable() {
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
      subtitle="Clerk is not configured. Merchant sign-up needs Platform Clerk keys."
    >
      <div className="space-y-4">
        <p className="text-sm leading-relaxed text-muted">
          Add Platform Clerk keys via <code className="text-primary">pnpm clerk:sync</code>, then
          refresh.
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

  // Already signed in: go to the dashboard and let the gate decide onboarding vs portal.
  useEffect(() => {
    if (isLoaded && isSignedIn) {
      router.replace("/dashboard");
    }
  }, [isLoaded, isSignedIn, router]);

  if (!isLoaded || isSignedIn) {
    return <MerchantAuthLoading label="Opening your portal…" />;
  }

  return (
    <MerchantAuthScreen
      mode="sign-up"
      title="Start with PorterChain"
      subtitle="Create your Clerk account (password stays here). Then fill the company file. Teammates use this same sign-up URL with the email your owner reserved."
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
        forceRedirectUrl="/dashboard"
        fallbackRedirectUrl="/dashboard"
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
