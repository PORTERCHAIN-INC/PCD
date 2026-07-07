"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { SignIn, SignOutButton, useAuth } from "@clerk/nextjs";
import { Shield, ShieldAlert } from "lucide-react";
import { isClerkConfigured } from "@/lib/env";

// Detects the sign-in <-> dashboard flicker: browser has a Clerk session but
// the server middleware can't verify it, so /dashboard bounces back to
// /sign-in?redirect_url=/dashboard and we redirect again, forever. Counts
// bounces within a short window so we can stop and surface the real cause.
const REDIRECT_GUARD_KEY = "pc_admin_signin_redirects";
const REDIRECT_GUARD_WINDOW_MS = 8000;
const REDIRECT_GUARD_MAX = 3;

function recordRedirectAttempt(): number {
  try {
    const now = Date.now();
    const raw = sessionStorage.getItem(REDIRECT_GUARD_KEY);
    let count = 0;
    if (raw) {
      const parsed = JSON.parse(raw) as { count: number; at: number };
      if (now - parsed.at < REDIRECT_GUARD_WINDOW_MS) count = parsed.count;
    }
    count += 1;
    sessionStorage.setItem(REDIRECT_GUARD_KEY, JSON.stringify({ count, at: now }));
    return count;
  } catch {
    return 1; // sessionStorage unavailable — allow the redirect.
  }
}

function clearRedirectGuard(): void {
  try {
    sessionStorage.removeItem(REDIRECT_GUARD_KEY);
  } catch {
    // ignore
  }
}

export default function SignInPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-gray-bg">
          <p className="text-sm text-muted">Loading…</p>
        </div>
      }
    >
      <SignInContent />
    </Suspense>
  );
}

function resolvePostSignInTarget(raw: string | null): string {
  const fallback = "/dashboard";
  if (!raw) return fallback;
  if (raw.startsWith("/") && !raw.startsWith("/sign-in")) return raw;
  try {
    const url = new URL(raw, "https://admin.porterchain.com");
    if (url.pathname.startsWith("/sign-in")) return fallback;
    return `${url.pathname}${url.search}${url.hash}` || fallback;
  } catch {
    return fallback;
  }
}

function SignInContent() {
  const searchParams = useSearchParams();
  const { isLoaded, isSignedIn } = useAuth();
  const redirectUrl = resolvePostSignInTarget(searchParams.get("redirect_url"));
  const [loopDetected, setLoopDetected] = useState(false);

  useEffect(() => {
    // A fresh, unauthenticated visit means any prior flicker is over.
    if (isLoaded && !isSignedIn) clearRedirectGuard();
  }, [isLoaded, isSignedIn]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    if (recordRedirectAttempt() > REDIRECT_GUARD_MAX) {
      // Server middleware keeps rejecting the session — stop looping and show why.
      setLoopDetected(true);
      return;
    }
    // Hard navigation so middleware receives the Clerk session cookie. Client-side
    // router.replace() can loop back to /sign-in with an infinite Loading state.
    window.location.assign(redirectUrl);
  }, [isLoaded, isSignedIn, redirectUrl]);

  if (isClerkConfigured() && loopDetected) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-bg p-4">
        <div className="w-full max-w-md rounded-2xl border border-amber-200 bg-white p-8 text-center shadow-sm">
          <ShieldAlert className="mx-auto h-12 w-12 text-amber-600" />
          <h1 className="mt-4 text-xl font-bold text-primary">Sign-in couldn’t complete</h1>
          <p className="mt-2 text-sm text-muted">
            You’re signed in, but the server couldn’t verify your session, so it kept returning to
            this page. This usually means the admin app’s <code>CLERK_SECRET_KEY</code> is missing
            at runtime or doesn’t match the <code>NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY</code> it was
            built with (they must be the same Clerk application).
          </p>
          <button
            type="button"
            onClick={() => {
              clearRedirectGuard();
              setLoopDetected(false);
              window.location.assign(redirectUrl);
            }}
            className="mt-6 w-full rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white hover:bg-secondary/90"
          >
            Try again
          </button>
          <SignOutButton redirectUrl="/sign-in">
            <button
              type="button"
              onClick={clearRedirectGuard}
              className="mt-2 w-full text-xs text-muted hover:text-secondary"
            >
              Sign out
            </button>
          </SignOutButton>
        </div>
      </div>
    );
  }

  if (!isClerkConfigured()) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-bg p-4">
        <div className="w-full max-w-md rounded-2xl border border-primary/10 bg-white p-8 shadow-sm">
          <h1 className="text-2xl font-bold text-primary">Porterchain Admin</h1>
          <p className="mt-2 text-sm text-muted">
            Clerk is not configured. Local dev uses API bypass — add staff in{" "}
            <code className="rounded bg-gray-bg px-1">admin_users</code> for production-like
            testing.
          </p>
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
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-secondary/10">
          <Shield className="h-7 w-7 text-secondary" />
        </div>
        <h1 className="text-2xl font-bold text-primary">Porterchain Admin</h1>
        <p className="mt-2 text-sm text-muted">
          Staff-only access. You must be provisioned in Admin Settings → Staff before you can use
          this console. Creating a Clerk account alone does not grant access.
        </p>
      </div>
      <SignIn
        routing="path"
        path="/sign-in"
        forceRedirectUrl="/dashboard"
        fallbackRedirectUrl="/dashboard"
        appearance={{
          elements: {
            footerAction: { display: "none" },
            footerActionLink: { display: "none" },
          },
        }}
      />
      <p className="mt-6 max-w-sm text-center text-xs text-muted">
        Need access? Ask a super admin to add your work email to the staff list.
      </p>
    </div>
  );
}
