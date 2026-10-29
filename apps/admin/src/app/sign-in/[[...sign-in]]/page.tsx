"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@porterchain/auth/oidc/client";
import { authDevBypassEnabled } from "@porterchain/auth/devBypass";
import {
  AuthLoadFailed,
  KeycloakSignInPanel,
  PortalAuthScreen,
  safeAppRedirect,
  signInUnavailableCopy,
  useAuthLoadTimeout,
} from "@porterchain/auth";
import { isAuthConfigured } from "@/lib/env";

/** Staff sign-in: Keycloak `pc-admin` hosted page (password + authenticator app). */
export default function SignInPage() {
  return (
    <Suspense
      fallback={
        <PortalAuthScreen portalLabel="Admin" title="Loading" subtitle="Preparing staff sign-in…">
          <p className="text-center text-sm text-muted">Loading…</p>
        </PortalAuthScreen>
      }
    >
      <StaffSignIn />
    </Suspense>
  );
}

function StaffSignIn() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isLoaded, isSignedIn } = useAuth();
  const loadTimedOut = useAuthLoadTimeout(isLoaded);
  const dev = authDevBypassEnabled();
  const redirectUrl = safeAppRedirect(searchParams.get("redirect_url"), {
    fallback: "/today",
    blockPrefixes: ["/sign-in", "/sign-up"],
  });
  const idle = searchParams.get("reason") === "idle";

  useEffect(() => {
    if (dev || (isLoaded && isSignedIn)) router.replace(redirectUrl);
  }, [dev, isLoaded, isSignedIn, redirectUrl, router]);

  if (!dev && !isAuthConfigured()) {
    return (
      <PortalAuthScreen
        portalLabel="Admin"
        title={signInUnavailableCopy.title}
        subtitle={signInUnavailableCopy.subtitle}
      >
        <p className="text-sm leading-relaxed text-muted">{signInUnavailableCopy.body}</p>
      </PortalAuthScreen>
    );
  }
  if (loadTimedOut) return <AuthLoadFailed />;

  return (
    <PortalAuthScreen
      portalLabel="Admin"
      title="Staff sign-in"
      subtitle={
        idle
          ? "You were signed out after inactivity. Sign in again to continue."
          : "Use your PorterChain staff account. Admin roles also need an authenticator app."
      }
    >
      <KeycloakSignInPanel returnTo={redirectUrl} primaryLabel="Continue to staff sign-in" />
    </PortalAuthScreen>
  );
}
