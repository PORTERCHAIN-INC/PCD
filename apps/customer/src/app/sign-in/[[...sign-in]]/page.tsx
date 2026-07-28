"use client";

import { Suspense, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { SignIn, useAuth } from "@clerk/nextjs";
import { isClerkConfigured, publicEnv } from "@/lib/env";

export default function SignInPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-gray-bg">
          <p className="text-sm text-muted">Loading…</p>
        </div>
      }
    >
      <SignInGate />
    </Suspense>
  );
}

function SignInGate() {
  if (!isClerkConfigured()) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-bg p-4">
        <div className="w-full max-w-md rounded-2xl border border-primary/10 bg-white p-8 shadow-sm">
          <h1 className="text-2xl font-bold text-primary">Porterchain Customer Portal</h1>
          <p className="mt-2 text-sm text-muted">Clerk is not configured for local development.</p>
          <Link
            href="/dashboard"
            className="mt-6 flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white hover:bg-secondary/90"
          >
            Continue in dev mode
          </Link>
        </div>
      </div>
    );
  }
  return <SignInContent />;
}

function SignInContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isLoaded, isSignedIn } = useAuth();
  const redirectUrl = searchParams.get("redirect_url") ?? "/onboarding";

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      router.replace(redirectUrl);
    }
  }, [isLoaded, isSignedIn, redirectUrl, router]);

  if (!isLoaded || isSignedIn) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-bg">
        <p className="text-sm text-muted">Loading…</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-bg p-4">
      <div className="mb-8 max-w-md text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-secondary/10 text-2xl font-bold text-secondary">
          P
        </div>
        <h1 className="text-2xl font-bold text-primary">Customer portal</h1>
        <p className="mt-2 text-sm text-muted">
          Sign in to view deliveries, invoices, and support tickets
        </p>
        <ul className="mt-6 space-y-2 text-left text-sm text-primary/80">
          <li>• Order history and active shipments</li>
          <li>• Invoices and payment receipts</li>
          <li>• Support tickets linked to your orders</li>
        </ul>
      </div>
      <div className="w-full max-w-md rounded-2xl border border-primary/10 bg-white p-4 shadow-sm">
        <SignIn
          routing="path"
          path="/sign-in"
          forceRedirectUrl={redirectUrl}
          fallbackRedirectUrl={redirectUrl}
        />
      </div>
      <p className="mt-8 max-w-sm text-center text-xs text-muted">
        Need to track one shipment without signing in?{" "}
        <a
          href={`${publicEnv.websiteUrl}/login`}
          className="font-semibold text-secondary hover:underline"
        >
          Use guest tracking on the website
        </a>
      </p>
    </div>
  );
}
