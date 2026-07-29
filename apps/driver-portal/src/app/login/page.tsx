"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { SignIn, useAuth, useUser } from "@clerk/nextjs";
import { isClerkConfigured, publicEnv } from "@/lib/env";
import { platformLoginUrl } from "@porterchain/auth";

function postLoginPath(redirectUrl: string | null): string {
  if (redirectUrl && redirectUrl !== "/" && redirectUrl.startsWith("/")) {
    return redirectUrl;
  }
  return "/onboarding";
}

function ClerkDriverContinue({ redirectUrl }: { redirectUrl: string | null }) {
  const router = useRouter();
  const { isSignedIn, isLoaded } = useAuth();
  const { user } = useUser();
  const [continuing, setContinuing] = useState(false);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    if (!user?.primaryEmailAddress?.emailAddress) return;
    setContinuing(true);
    router.replace(postLoginPath(redirectUrl));
  }, [isLoaded, isSignedIn, redirectUrl, router, user]);

  if (!isLoaded) {
    return (
      <div className="w-full rounded-2xl bg-white p-8 text-center shadow-sm">
        <p className="text-sm text-[var(--muted)]">Loading sign-in…</p>
      </div>
    );
  }

  if (isSignedIn) {
    return (
      <div className="w-full rounded-2xl bg-white p-8 shadow-sm">
        {continuing ? <p className="text-sm text-[var(--muted)]">Opening driver portal…</p> : null}
      </div>
    );
  }

  return (
    <div className="w-full rounded-2xl bg-white p-4 shadow-sm">
      <SignIn
        routing="hash"
        signUpUrl={undefined}
        fallbackRedirectUrl={postLoginPath(redirectUrl)}
        appearance={{
          elements: {
            rootBox: "w-full",
            card: "shadow-none border-0",
            footerAction: { display: "none" },
          },
        }}
      />
    </div>
  );
}

function LoginPageContent() {
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect_url");

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--gray-bg)] p-6">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-xl font-bold">Porterchain Driver</h1>
          <p className="mt-1 text-sm text-[var(--muted)]">
            {isClerkConfigured()
              ? `Sign in with your approved driver account. Prefer Platform login at ${platformLoginUrl(publicEnv.websiteUrl)}.`
              : "Clerk is not configured for this environment."}
          </p>
        </div>

        {isClerkConfigured() ? <ClerkDriverContinue redirectUrl={redirectUrl} /> : null}
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-[var(--gray-bg)] p-6">
          <p className="text-sm text-[var(--muted)]">Loading…</p>
        </div>
      }
    >
      <LoginPageContent />
    </Suspense>
  );
}
