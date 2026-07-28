"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useSignIn } from "@clerk/nextjs/legacy";
import { isClerkConfigured } from "@/lib/env";

const PROVIDER_STRATEGY: Record<string, "oauth_google" | "oauth_microsoft"> = {
  google: "oauth_google",
  microsoft: "oauth_microsoft",
};

export default function MerchantOAuthKickoffPage() {
  const params = useParams<{ provider: string }>();
  const provider = params.provider ?? "";
  const strategy = PROVIDER_STRATEGY[provider];

  if (!isClerkConfigured()) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-bg p-4">
        <p className="text-sm text-muted">Clerk is not configured in this environment.</p>
      </div>
    );
  }

  if (!strategy) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-gray-bg p-4">
        <p className="text-sm text-muted">Unknown sign-in provider.</p>
        <Link href="/sign-in" className="mt-4 text-sm font-medium text-secondary hover:underline">
          Back to sign in
        </Link>
      </div>
    );
  }

  return <OAuthKickoffWithClerk provider={provider} strategy={strategy} />;
}

function OAuthKickoffWithClerk({
  provider,
  strategy,
}: {
  provider: string;
  strategy: "oauth_google" | "oauth_microsoft";
}) {
  const { isLoaded, signIn } = useSignIn();

  useEffect(() => {
    if (!isLoaded || !signIn) return;
    void signIn.authenticateWithRedirect({
      strategy,
      redirectUrl: "/sign-in/sso-callback",
      redirectUrlComplete: "/onboarding",
    });
  }, [isLoaded, signIn, strategy]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-bg">
      <p className="text-sm text-muted">Redirecting to {provider}…</p>
    </div>
  );
}
