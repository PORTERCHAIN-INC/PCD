"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { SignIn, useAuth, useUser } from "@clerk/nextjs";
import {
  PortalAuthScreen,
  platformLoginUrl,
  porterchainClerkAppearanceInviteOnly,
  safeAppRedirect,
} from "@porterchain/auth";
import { isClerkConfigured, publicEnv } from "@/lib/env";

function ClerkDriverContinue({ redirectUrl }: { redirectUrl: string }) {
  const router = useRouter();
  const { isSignedIn, isLoaded } = useAuth();
  const { user } = useUser();
  const [continuing, setContinuing] = useState(false);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    if (!user?.primaryEmailAddress?.emailAddress) return;
    setContinuing(true);
    router.replace(redirectUrl);
  }, [isLoaded, isSignedIn, redirectUrl, router, user]);

  if (!isLoaded) {
    return (
      <p className="text-center text-sm text-muted" role="status">
        Loading sign-in…
      </p>
    );
  }

  if (isSignedIn) {
    return (
      <p className="text-center text-sm text-muted" role="status">
        {continuing ? "Opening driver portal…" : "Preparing…"}
      </p>
    );
  }

  return (
    <SignIn
      routing="path"
      path="/login"
      signUpUrl={undefined}
      forceRedirectUrl={redirectUrl}
      fallbackRedirectUrl={redirectUrl}
      appearance={porterchainClerkAppearanceInviteOnly}
    />
  );
}

function LoginPageContent() {
  const searchParams = useSearchParams();
  const redirectUrl = safeAppRedirect(searchParams.get("redirect_url"), {
    fallback: "/onboarding",
    blockPrefixes: ["/login", "/sign-in", "/sign-up"],
  });

  if (!isClerkConfigured()) {
    const platformUrl = platformLoginUrl(publicEnv.websiteUrl);
    return (
      <PortalAuthScreen
        portalLabel="Driver"
        title="Local development"
        subtitle="Clerk is not configured for this environment."
        unavailable={
          <>
            <h1 className="text-xl font-semibold text-primary">Driver portal</h1>
            <p className="mt-2 text-sm text-muted">
              Configure Clerk keys to enable driver sign-in.
            </p>
            <a
              href={platformUrl}
              className="mt-6 flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white hover:bg-[#1d4ed8]"
            >
              Platform login
            </a>
          </>
        }
      />
    );
  }

  return (
    <PortalAuthScreen
      portalLabel="Driver"
      title="Driver sign-in"
      subtitle="Invitation-only access for approved vehicle partners."
      websiteUrl={publicEnv.websiteUrl}
      showPlatformLogin
      footer={
        <>Need access? Contact Porterchain operations after your partner application is approved.</>
      }
    >
      <ClerkDriverContinue redirectUrl={redirectUrl} />
    </PortalAuthScreen>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <PortalAuthScreen portalLabel="Driver" title="Loading" subtitle="Preparing sign-in…">
          <p className="text-center text-sm text-muted">Loading…</p>
        </PortalAuthScreen>
      }
    >
      <LoginPageContent />
    </Suspense>
  );
}
