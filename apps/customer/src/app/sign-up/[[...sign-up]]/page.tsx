"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { SignUp, useAuth } from "@clerk/nextjs";
import {
  PasswordRequirements,
  porterchainClerkAppearance,
  signUpUnavailableCopy,
} from "@porterchain/auth";
import { isDevelopmentBuild } from "@porterchain/auth/devBypass";
import { CustomerAuthLoading, CustomerAuthScreen } from "@/components/auth/CustomerAuthScreen";
import { isClerkConfigured } from "@/lib/env";

export default function SignUpPage() {
  if (!isClerkConfigured()) {
    return <ClerkUnavailable />;
  }
  return <SignUpWithClerk />;
}

function ClerkUnavailable() {
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
      subtitle="Clerk is not configured for this environment."
    >
      <div className="space-y-4">
        <p className="text-sm leading-relaxed text-muted">
          Add Platform Clerk keys via <code className="text-primary">pnpm clerk:sync</code>, then
          refresh.
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

function SignUpWithClerk() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      router.replace("/onboarding");
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
      <SignUp
        routing="path"
        path="/sign-up"
        signInUrl="/sign-in"
        forceRedirectUrl="/onboarding"
        fallbackRedirectUrl="/onboarding"
        appearance={porterchainClerkAppearance}
      />
      <PasswordRequirements />
    </CustomerAuthScreen>
  );
}
